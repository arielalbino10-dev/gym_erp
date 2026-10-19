"""Persistencia identity / credenciales / sesiones en gym_platform_test (H2-B.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.errors import (
    CredentialDuplicateUserError,
    IdentityDuplicateEmailError,
    IdentityStorageError,
    IdentityUpdateConflictError,
    SessionExpiredError,
    SessionRevokedError,
)
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
    generate_opaque_session_token,
    hash_session_token,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid

pytestmark = [
    pytest.mark.integration,
    pytest.mark.identity_persistence,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_identity_round_trip_and_lookup(mongo_identity_repository):
    moment = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    identity = UserIdentity.create(email="persist.user@example.test", now=moment)
    await mongo_identity_repository.save(identity)

    by_id = await mongo_identity_repository.get_by_id(identity.user_id)
    by_email = await mongo_identity_repository.get_by_email_normalized("persist.user@example.test")
    assert by_id == identity
    assert by_email == identity


async def test_identity_email_normalized_unique(mongo_identity_repository):
    moment = datetime(2026, 5, 1, tzinfo=UTC)
    first = UserIdentity.create(email="Unique@Example.test", now=moment)
    await mongo_identity_repository.save(first)
    second = UserIdentity.create(email="unique@example.test", now=moment)
    with pytest.raises(IdentityDuplicateEmailError):
        await mongo_identity_repository.save(second)


async def test_identity_update_conflict_on_stale_updated_at(mongo_identity_repository):
    moment = datetime(2026, 5, 2, tzinfo=UTC)
    identity = UserIdentity.create(email="conflict@example.test", now=moment)
    await mongo_identity_repository.save(identity)
    stale = identity
    updated = identity.increment_credential_version(now=moment + timedelta(seconds=1))
    await mongo_identity_repository.save(updated, expected_updated_at=identity.updated_at)
    with pytest.raises(IdentityUpdateConflictError):
        await mongo_identity_repository.save(
            stale.increment_credential_version(now=moment + timedelta(seconds=2)),
            expected_updated_at=stale.updated_at,
        )


async def test_credential_stores_argon2id_only(
    mongo_identity_repository,
    mongo_credential_repository,
):
    moment = datetime(2026, 5, 3, tzinfo=UTC)
    identity = UserIdentity.create(email="cred@example.test", now=moment)
    await mongo_identity_repository.save(identity)
    hasher = Argon2PasswordHasher()
    stored_hash = hasher.hash("integration-test-password-12")
    credential = UserCredential.create(
        user_id=identity.user_id,
        password_hash=stored_hash,
        credential_version=0,
        now=moment,
    )
    await mongo_credential_repository.insert(credential)
    restored = await mongo_credential_repository.get_by_user_id(identity.user_id)
    assert restored is not None
    assert restored.password_hash.startswith("$argon2id$")
    assert "integration-test-password" not in restored.password_hash


async def test_credential_unique_per_user(mongo_identity_repository, mongo_credential_repository):
    moment = datetime(2026, 5, 4, tzinfo=UTC)
    identity = UserIdentity.create(email="onecred@example.test", now=moment)
    await mongo_identity_repository.save(identity)
    hasher = Argon2PasswordHasher()
    first = UserCredential.create(
        user_id=identity.user_id,
        password_hash=hasher.hash("integration-test-password-12"),
        credential_version=0,
        now=moment,
    )
    await mongo_credential_repository.insert(first)
    duplicate = UserCredential.create(
        user_id=identity.user_id,
        password_hash=hasher.hash("integration-test-password-13"),
        credential_version=1,
        now=moment,
    )
    with pytest.raises(CredentialDuplicateUserError):
        await mongo_credential_repository.insert(duplicate)


async def test_session_persists_token_hash_not_plain_token(mongo_auth_session_repository):
    moment = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    raw_token = generate_opaque_session_token()
    token_hash = hash_session_token(raw_token)
    session = AuthSession.create(
        user_id=new_uuid(),
        session_kind=SessionKind.PLATFORM,
        token_hash=token_hash,
        expires_at=moment + timedelta(hours=8),
        idle_expires_at=moment + timedelta(minutes=30),
        credential_version=0,
        now=moment,
    )
    await mongo_auth_session_repository.insert(session)
    restored = await mongo_auth_session_repository.get_by_token_hash(token_hash)
    assert restored is not None
    assert restored.token_hash == token_hash
    assert raw_token != restored.token_hash


async def test_session_lookup_revocation_and_kinds(mongo_auth_session_repository):
    moment = datetime(2026, 5, 6, tzinfo=UTC)
    user_id = new_uuid()
    token_platform = hash_session_token(generate_opaque_session_token())
    token_gym = hash_session_token(generate_opaque_session_token())
    platform = AuthSession.create(
        user_id=user_id,
        session_kind=SessionKind.PLATFORM,
        token_hash=token_platform,
        expires_at=moment + timedelta(hours=12),
        idle_expires_at=moment + timedelta(minutes=15),
        credential_version=1,
        now=moment,
    )
    gym = AuthSession.create(
        user_id=user_id,
        session_kind=SessionKind.GYM,
        token_hash=token_gym,
        expires_at=moment + timedelta(hours=8),
        idle_expires_at=moment + timedelta(minutes=30),
        credential_version=1,
        active_tenant_id=new_uuid(),
        now=moment,
    )
    await mongo_auth_session_repository.insert(platform)
    await mongo_auth_session_repository.insert(gym)

    found = await mongo_auth_session_repository.get_by_token_hash(token_platform)
    assert found is not None
    assert found.session_kind is SessionKind.PLATFORM

    revoked = platform.revoke(reason="logout", now=moment)
    await mongo_auth_session_repository.save_revoked(revoked)
    with pytest.raises(SessionRevokedError):
        (await mongo_auth_session_repository.get_by_id(platform.session_id)).assert_usable_at(
            moment + timedelta(minutes=1)
        )

    count = await mongo_auth_session_repository.revoke_all_for_user(
        user_id,
        reason="password_change",
        revoked_at=moment + timedelta(minutes=2),
    )
    assert count == 1
    gym_restored = await mongo_auth_session_repository.get_by_id(gym.session_id)
    assert gym_restored is not None
    assert gym_restored.is_revoked()


async def test_session_expiration_checks(mongo_auth_session_repository):
    moment = datetime(2026, 5, 7, tzinfo=UTC)
    session = AuthSession.create(
        user_id=new_uuid(),
        session_kind=SessionKind.GYM,
        token_hash=hash_session_token(generate_opaque_session_token()),
        expires_at=moment + timedelta(minutes=5),
        idle_expires_at=moment + timedelta(minutes=1),
        credential_version=0,
        now=moment,
    )
    await mongo_auth_session_repository.insert(session)
    restored = await mongo_auth_session_repository.get_by_id(session.session_id)
    assert restored is not None
    with pytest.raises(SessionExpiredError):
        restored.assert_usable_at(moment + timedelta(minutes=2))


async def test_session_touch_activity_concurrent(mongo_auth_session_repository):
    moment = datetime(2026, 5, 8, tzinfo=UTC)
    session = AuthSession.create(
        user_id=new_uuid(),
        session_kind=SessionKind.PLATFORM,
        token_hash=hash_session_token(generate_opaque_session_token()),
        expires_at=moment + timedelta(hours=2),
        idle_expires_at=moment + timedelta(minutes=15),
        credential_version=0,
        now=moment,
    )
    await mongo_auth_session_repository.insert(session)
    expected_idle = moment + timedelta(minutes=20)
    touch_now = moment + timedelta(minutes=5)
    touched = session.touch_activity(idle_expires_at=expected_idle, now=touch_now)
    updated = await mongo_auth_session_repository.touch_activity(
        touched,
        expected_last_seen_at=session.last_seen_at,
    )
    assert updated.last_seen_at == touched.last_seen_at
    assert updated.idle_expires_at == expected_idle


async def test_storage_error_does_not_leak_secrets(mongo_auth_session_repository):
    moment = datetime(2026, 5, 9, tzinfo=UTC)
    secret = generate_opaque_session_token()
    session = AuthSession.create(
        user_id=new_uuid(),
        session_kind=SessionKind.PLATFORM,
        token_hash=hash_session_token(secret),
        expires_at=moment + timedelta(hours=1),
        idle_expires_at=moment + timedelta(minutes=10),
        credential_version=0,
        now=moment,
    )
    await mongo_auth_session_repository.insert(session)
    duplicate = AuthSession.create(
        user_id=new_uuid(),
        session_kind=SessionKind.PLATFORM,
        token_hash=session.token_hash,
        expires_at=moment + timedelta(hours=1),
        idle_expires_at=moment + timedelta(minutes=10),
        credential_version=0,
        now=moment,
    )
    with pytest.raises(IdentityStorageError) as exc_info:
        await mongo_auth_session_repository.insert(duplicate)
    assert secret not in str(exc_info.value)

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from gym_erp_api.modules.identity.application.errors import AuthenticationFailedError
from gym_erp_api.modules.identity.application.services.credential_verification_service import (
    CredentialVerificationService,
)
from gym_erp_api.modules.identity.domain.enums import UserIdentityStatus
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
    InvalidStoredPasswordHashError,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid

PASSWORD = "integration-test-password-12"


@pytest.fixture
def hasher():
    return Argon2PasswordHasher()


@pytest.fixture
def identity_repo():
    return AsyncMock()


@pytest.fixture
def credential_repo():
    return AsyncMock()


@pytest.fixture
def service(hasher, identity_repo, credential_repo):
    return CredentialVerificationService(
        identities=identity_repo,
        credentials=credential_repo,
        password_hasher=hasher,
    )


def _active_identity(email: str = "user@example.test") -> UserIdentity:
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    return UserIdentity.create(email=email, user_id=new_uuid(), now=moment).mark_email_verified(
        now=moment
    )


@pytest.mark.asyncio
async def test_verify_success(service, identity_repo, credential_repo, hasher):
    identity = _active_identity()
    identity_repo.get_by_email_normalized.return_value = identity
    credential_repo.get_by_user_id.return_value = UserCredential.create(
        user_id=identity.user_id,
        password_hash=hasher.hash(PASSWORD),
        credential_version=0,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    principal = await service.verify(email="user@example.test", password=PASSWORD)
    assert principal.user_id == identity.user_id
    assert principal.credential_version == 0


@pytest.mark.asyncio
async def test_verify_wrong_password(service, identity_repo, credential_repo, hasher):
    identity = _active_identity()
    identity_repo.get_by_email_normalized.return_value = identity
    credential_repo.get_by_user_id.return_value = UserCredential.create(
        user_id=identity.user_id,
        password_hash=hasher.hash(PASSWORD),
        credential_version=0,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(AuthenticationFailedError):
        await service.verify(email="user@example.test", password="wrong-password-value")


@pytest.mark.asyncio
async def test_verify_unknown_user(service, identity_repo, credential_repo):
    identity_repo.get_by_email_normalized.return_value = None
    with pytest.raises(AuthenticationFailedError):
        await service.verify(email="missing@example.test", password=PASSWORD)


@pytest.mark.parametrize(
    "status",
    [
        UserIdentityStatus.LOCKED,
        UserIdentityStatus.DISABLED,
        UserIdentityStatus.PENDING_VERIFICATION,
    ],
)
@pytest.mark.asyncio
async def test_verify_rejects_non_active_status(
    service, identity_repo, credential_repo, hasher, status
):
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    identity = UserIdentity.create(email="x@example.test", now=moment)
    if status is UserIdentityStatus.LOCKED:
        identity = identity.mark_email_verified(now=moment).transition_status(
            UserIdentityStatus.LOCKED,
            now=moment,
        )
    elif status is UserIdentityStatus.DISABLED:
        identity = identity.transition_status(UserIdentityStatus.DISABLED, now=moment)
    identity_repo.get_by_email_normalized.return_value = identity
    credential_repo.get_by_user_id.return_value = UserCredential.create(
        user_id=identity.user_id,
        password_hash=hasher.hash(PASSWORD),
        credential_version=0,
        now=moment,
    )
    with pytest.raises(AuthenticationFailedError):
        await service.verify(email="x@example.test", password=PASSWORD)


@pytest.mark.asyncio
async def test_verify_invalid_stored_hash(service, identity_repo, credential_repo):
    identity = _active_identity()
    identity_repo.get_by_email_normalized.return_value = identity
    credential_repo.get_by_user_id.return_value = UserCredential.create(
        user_id=identity.user_id,
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$notvalid",
        credential_version=0,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(AuthenticationFailedError):
        await service.verify(email="user@example.test", password=PASSWORD)


@pytest.mark.asyncio
async def test_verify_invalid_hash_raises_domain_not_leak(monkeypatch, service, identity_repo):
    identity_repo.get_by_email_normalized.return_value = None

    async def boom(*_a, **_k):
        raise InvalidStoredPasswordHashError("bad")

    monkeypatch.setattr(
        "gym_erp_api.modules.identity.application.services.credential_verification_service.verify_password_async",
        boom,
    )
    with pytest.raises(AuthenticationFailedError):
        await service.verify(email="a@b.co", password=PASSWORD)

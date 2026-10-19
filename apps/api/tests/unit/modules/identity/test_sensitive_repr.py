from datetime import UTC, datetime

from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.shared_kernel.identifiers import new_uuid


def test_credential_repr_hides_password_hash():
    secret = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$abcdefghijklmnop"
    credential = UserCredential.create(
        user_id=new_uuid(),
        password_hash=secret,
        credential_version=0,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    rendered = repr(credential)
    assert secret not in rendered
    assert "password_hash" not in rendered or "..." not in rendered


def test_auth_session_repr_hides_token_hash():
    token_hash = "f" * 64
    session = AuthSession.create(
        user_id=new_uuid(),
        session_kind=SessionKind.PLATFORM,
        token_hash=token_hash,
        expires_at=datetime(2026, 1, 2, tzinfo=UTC),
        idle_expires_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        credential_version=0,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    rendered = repr(session)
    assert token_hash not in rendered

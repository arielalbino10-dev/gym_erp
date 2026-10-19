from datetime import UTC, datetime

from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.mongo.auth_session_document_mapper import (
    auth_session_from_document,
    auth_session_to_document,
)
from gym_erp_api.modules.identity.infrastructure.mongo.credential_document_mapper import (
    credential_from_document,
    credential_to_document,
)
from gym_erp_api.modules.identity.infrastructure.mongo.identity_document_mapper import (
    identity_from_document,
    identity_to_document,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid


def test_identity_mapper_round_trip():
    moment = datetime(2026, 3, 1, tzinfo=UTC)
    identity = UserIdentity.create(email="mapper@example.test", now=moment)
    doc = identity_to_document(identity)
    assert doc["_id"] == identity.user_id
    assert identity_from_document(doc) == identity


def test_credential_mapper_round_trip():
    moment = datetime(2026, 3, 2, tzinfo=UTC)
    credential = UserCredential.create(
        user_id=new_uuid(),
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHQ$hash",
        credential_version=2,
        now=moment,
    )
    doc = credential_to_document(credential)
    assert credential_from_document(doc) == credential


def test_auth_session_mapper_round_trip():
    moment = datetime(2026, 3, 3, tzinfo=UTC)
    session = AuthSession.create(
        user_id=new_uuid(),
        session_kind=SessionKind.PLATFORM,
        token_hash="c" * 64,
        expires_at=moment,
        idle_expires_at=moment,
        credential_version=1,
        now=moment,
    )
    doc = auth_session_to_document(session)
    assert auth_session_from_document(doc) == session

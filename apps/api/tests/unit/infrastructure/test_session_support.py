from unittest.mock import MagicMock

import pytest
from pymongo.asynchronous.client_session import AsyncClientSession

from gym_erp_api.infrastructure.mongo.session_support import ensure_pymongo_session
from gym_erp_api.infrastructure.mongo.uow_errors import InvalidMongoSessionError


def test_rejects_session_without_active_transaction():
    session = MagicMock(spec=AsyncClientSession)
    session.has_ended = False
    session.in_transaction = False
    session.client = MagicMock()
    with pytest.raises(InvalidMongoSessionError, match="transacción"):
        ensure_pymongo_session(session, require_in_transaction=True)


def test_rejects_ended_session():
    session = MagicMock(spec=AsyncClientSession)
    session.has_ended = True
    session.in_transaction = True
    session.client = MagicMock()
    with pytest.raises(InvalidMongoSessionError, match="finalizada"):
        ensure_pymongo_session(session)


def test_rejects_session_from_other_client():
    session = MagicMock(spec=AsyncClientSession)
    session.has_ended = False
    session.in_transaction = True
    session.client = MagicMock()
    expected = MagicMock()
    with pytest.raises(InvalidMongoSessionError, match="AsyncMongoClient"):
        ensure_pymongo_session(session, expected_client=expected, require_in_transaction=True)

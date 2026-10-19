from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pymongo.errors import DuplicateKeyError

from gym_erp_api.modules.identity.domain.errors import (
    IdentityDuplicateEmailError,
    IdentityUpdateConflictError,
)
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_identity_repository import (
    MongoIdentityRepository,
)


@pytest.fixture
def identity_collection():
    collection = MagicMock()
    collection.database.client = MagicMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock(return_value=None)
    collection.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
    return collection


@pytest.mark.asyncio
async def test_insert_on_save_without_expected_updated_at(identity_collection):
    repo = MongoIdentityRepository(identity_collection)
    identity = UserIdentity.create(email="repo@example.test", now=datetime(2026, 1, 1, tzinfo=UTC))
    await repo.save(identity)
    identity_collection.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_email_maps_to_domain_error(identity_collection):
    identity_collection.insert_one = AsyncMock(
        side_effect=DuplicateKeyError("dup", 11000, {"keyPattern": {"email_normalized": 1}})
    )
    repo = MongoIdentityRepository(identity_collection)
    identity = UserIdentity.create(email="dup@example.test", now=datetime(2026, 1, 1, tzinfo=UTC))
    with pytest.raises(IdentityDuplicateEmailError):
        await repo.save(identity)


@pytest.mark.asyncio
async def test_update_conflict_when_stale_timestamp(identity_collection):
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    identity = UserIdentity.create(email="stale@example.test", now=moment)
    identity_collection.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
    identity_collection.find_one = AsyncMock(
        return_value={
            "_id": identity.user_id,
            "user_id": identity.user_id,
            "email": identity.email,
            "email_normalized": identity.email_normalized,
            "status": identity.status.value,
            "credential_version": 0,
            "created_at": moment,
            "updated_at": moment,
        }
    )
    repo = MongoIdentityRepository(identity_collection)
    with pytest.raises(IdentityUpdateConflictError):
        await repo.save(identity, expected_updated_at=moment)

from unittest.mock import MagicMock

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases


def test_mongo_databases_exposes_platform_and_operational():
    client = MagicMock()
    client.__getitem__.side_effect = lambda name: f"db:{name}"
    settings = Settings(
        app_env="test",
        mongodb_uri=None,
        mongodb_platform_db="gym_platform",
        mongodb_operational_db="gym_operational",
    )
    dbs = MongoDatabases(client, settings)
    assert dbs.platform == "db:gym_platform"
    assert dbs.operational == "db:gym_operational"

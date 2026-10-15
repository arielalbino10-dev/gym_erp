"""Acceso a bases platform y operational con un solo AsyncMongoClient."""

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from gym_erp_api.core.config import Settings


class MongoDatabases:
    def __init__(self, client: AsyncMongoClient, settings: Settings) -> None:
        self._client = client
        self._platform_name = settings.mongodb_platform_db
        self._operational_name = settings.mongodb_operational_db

    @property
    def client(self) -> AsyncMongoClient:
        return self._client

    @property
    def platform(self) -> AsyncDatabase:
        return self._client[self._platform_name]

    @property
    def operational(self) -> AsyncDatabase:
        return self._client[self._operational_name]

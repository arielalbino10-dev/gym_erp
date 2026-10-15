"""CreateOrganizationHandler — orquestación transaccional (mocks, sin Mongo)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from gym_erp_api.infrastructure.mongo.uow_errors import MongoTransactionCommitUncertainError
from gym_erp_api.modules.organization.application.bootstrap_context import (
    CREATE_ORGANIZATION_BOOTSTRAP_MEMBERSHIP_ID,
    CREATE_ORGANIZATION_BOOTSTRAP_USER_ID,
)
from gym_erp_api.modules.organization.application.commands.create_organization import (
    CreateOrganizationCommand,
    CreateOrganizationResult,
)
from gym_erp_api.modules.organization.application.create_organization_fingerprint import (
    create_organization_request_fingerprint,
)
from gym_erp_api.modules.organization.application.errors import (
    IdempotencyAlreadyCompletedError,
    IdempotencyInProgressError,
    IdempotencyPayloadConflictError,
    OrganizationCommitUncertainError,
)
from gym_erp_api.modules.organization.application.idempotency_constants import (
    CREATE_ORGANIZATION_OPERATION,
)
from gym_erp_api.modules.organization.application.ports.idempotency_store import (
    IdempotencyRecord,
    IdempotencyRecordStatus,
)
from gym_erp_api.modules.organization.application.use_cases.create_organization_handler import (
    CreateOrganizationHandler,
)
from gym_erp_api.modules.organization.domain.enums import BranchStatus, TenantStatus
from tests.support.tenant_fixtures import USER_A_ID

FIXED_NOW = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
TENANT_ID = "a0000000-0000-4000-8000-000000000001"
BRANCH_ID = "b0000000-0000-4000-8000-000000000002"
OTHER_TENANT_ID = "c0000000-0000-4000-8000-000000000003"
OTHER_BRANCH_ID = "d0000000-0000-4000-8000-000000000004"

HANDLER_SOURCE = (
    Path(__file__).resolve().parents[5]
    / "src"
    / "gym_erp_api"
    / ("modules/organization/application/use_cases/create_organization_handler.py")
)


def _command(**overrides: Any) -> CreateOrganizationCommand:
    base = {
        "idempotency_key": "req-handler-001",
        "legal_name": "Legal SA",
        "display_name": "Gym Display",
        "branch_name": "Centro",
    }
    base.update(overrides)
    return CreateOrganizationCommand.build(**base)


def _completed_record(
    command: CreateOrganizationCommand,
    result: CreateOrganizationResult,
    fingerprint: str,
) -> IdempotencyRecord:
    return IdempotencyRecord(
        operation=CREATE_ORGANIZATION_OPERATION,
        idempotency_key=command.idempotency_key,
        status=IdempotencyRecordStatus.COMPLETED,
        request_fingerprint=fingerprint,
        tenant_id=result.tenant_id,
        branch_id=result.branch_id,
        result=result,
    )


def _stored_result(*, replayed: bool = False) -> CreateOrganizationResult:
    return CreateOrganizationResult(
        tenant_id=OTHER_TENANT_ID,
        branch_id=OTHER_BRANCH_ID,
        tenant_status=TenantStatus.ACTIVE,
        branch_status=BranchStatus.ACTIVE,
        idempotency_replayed=replayed,
        created_at=FIXED_NOW,
    )


@dataclass
class _CallLog:
    names: list[str] = field(default_factory=list)

    def record(self, name: str) -> None:
        self.names.append(name)


class _FakeUow:
    def __init__(
        self,
        *,
        exit_error: BaseException | None = None,
        log: _CallLog | None = None,
    ) -> None:
        self.session = object()
        self._exit_error = exit_error
        self._log = log

    async def __aenter__(self) -> _FakeUow:
        if self._log:
            self._log.record("uow_enter")
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._log:
            self._log.record("uow_exit")
        if exc_type is None and self._exit_error is not None:
            raise self._exit_error


class _FakeIdempotencyStore:
    def __init__(
        self,
        *,
        preflight: IdempotencyRecord | None = None,
        second_find: IdempotencyRecord | None = None,
        reserve_raises: BaseException | None = None,
        log: _CallLog | None = None,
    ) -> None:
        self._preflight = preflight
        self._second_find = second_find
        self._reserve_raises = reserve_raises
        self._log = log
        self.find_calls = 0
        self.mark_completed_calls = 0

    async def find_by_operation_and_key(
        self,
        operation: str,
        idempotency_key: str,
        *,
        session: object | None = None,
    ) -> IdempotencyRecord | None:
        self.find_calls += 1
        if session is not None:
            raise AssertionError("find no debe reutilizar sesión transaccional")
        if self.find_calls == 1:
            return self._preflight
        return self._second_find

    async def reserve(self, reservation: object, *, session: object) -> None:
        if self._log:
            self._log.record("reserve")
        if self._reserve_raises:
            raise self._reserve_raises

    async def mark_completed(
        self,
        operation: str,
        idempotency_key: str,
        *,
        result: CreateOrganizationResult,
        session: object,
    ) -> None:
        if self._log:
            self._log.record("mark_completed")
        self.mark_completed_calls += 1


@dataclass
class _FactoryCapture:
    kwargs: dict[str, str] | None = None


class _RecordingBranchRepo:
    def __init__(self, log: _CallLog, session_sink: list[object | None]) -> None:
        self._log = log
        self._session_sink = session_sink

    async def insert(self, branch: object, *, session: object | None = None) -> None:
        self._log.record("branch_insert")
        self._session_sink.append(session)
        assert getattr(branch, "tenant_id") == TENANT_ID

    async def get_by_id(self, branch_id: str, *, session: object | None = None) -> object | None:
        return None


class _RecordingTenantRepo:
    def __init__(self, log: _CallLog, session_sink: list[object | None]) -> None:
        self._log = log
        self._session_sink = session_sink

    async def insert(self, tenant: object, *, session: object | None = None) -> None:
        self._log.record("tenant_insert")
        self._session_sink.append(session)
        assert getattr(tenant, "status") == TenantStatus.PROVISIONING

    async def get_by_id(self, tenant_id: str, *, session: object | None = None) -> object | None:
        return None

    async def exists_by_id(self, tenant_id: str, *, session: object | None = None) -> bool:
        return False

    async def save(self, tenant: object, *, session: object | None = None) -> None:
        self._log.record("tenant_save_active")
        self._session_sink.append(session)
        assert getattr(tenant, "status") == TenantStatus.ACTIVE


class _StubBranchRepositoryFactory:
    def __init__(
        self,
        capture: _FactoryCapture,
        repo: _RecordingBranchRepo,
    ) -> None:
        self._capture = capture
        self._repo = repo

    def for_provisioned_tenant(
        self,
        *,
        tenant_id: str,
        allowed_branch_id: str,
        actor_user_id: str,
        actor_membership_id: str,
    ) -> _RecordingBranchRepo:
        self._capture.kwargs = {
            "tenant_id": tenant_id,
            "allowed_branch_id": allowed_branch_id,
            "actor_user_id": actor_user_id,
            "actor_membership_id": actor_membership_id,
        }
        return self._repo


def _build_handler(
    *,
    idempotency: _FakeIdempotencyStore,
    log: _CallLog,
    session_sink: list[object | None],
    factory_capture: _FactoryCapture,
    uow: _FakeUow,
    id_generator: Any,
    branch_repo: _RecordingBranchRepo | None = None,
) -> CreateOrganizationHandler:
    repo = branch_repo or _RecordingBranchRepo(log, session_sink)
    branch_factory = _StubBranchRepositoryFactory(factory_capture, repo)

    return CreateOrganizationHandler(
        idempotency_store=idempotency,
        tenant_repository=_RecordingTenantRepo(log, session_sink),
        branch_repository_factory=branch_factory,
        unit_of_work_factory=lambda: uow,
        id_generator=id_generator,
        clock=lambda: FIXED_NOW,
    )


@pytest.mark.asyncio
async def test_successful_provision_order_and_shared_session():
    log = _CallLog()
    sessions: list[object | None] = []
    uow = _FakeUow(log=log)
    ids = iter([TENANT_ID, BRANCH_ID])
    handler = _build_handler(
        idempotency=_FakeIdempotencyStore(log=log),
        log=log,
        session_sink=sessions,
        factory_capture=_FactoryCapture(),
        uow=uow,
        id_generator=lambda: next(ids),
    )

    result = await handler.execute(_command())

    assert result.tenant_id == TENANT_ID
    assert result.branch_id == BRANCH_ID
    assert result.tenant_status == TenantStatus.ACTIVE
    assert result.branch_status == BranchStatus.ACTIVE
    assert result.idempotency_replayed is False
    assert log.names == [
        "uow_enter",
        "reserve",
        "tenant_insert",
        "branch_insert",
        "tenant_save_active",
        "mark_completed",
        "uow_exit",
    ]
    assert len(sessions) == 3
    assert sessions[0] is uow.session
    assert sessions[1] is uow.session
    assert sessions[2] is uow.session


@pytest.mark.asyncio
async def test_tenant_and_branch_share_tenant_id_via_domain():
    log = _CallLog()
    sessions: list[object | None] = []
    ids = iter([TENANT_ID, BRANCH_ID])
    handler = _build_handler(
        idempotency=_FakeIdempotencyStore(log=log),
        log=log,
        session_sink=sessions,
        factory_capture=_FactoryCapture(),
        uow=_FakeUow(log=log),
        id_generator=lambda: next(ids),
    )
    result = await handler.execute(_command())
    assert result.tenant_id == TENANT_ID
    assert result.branch_id == BRANCH_ID


@pytest.mark.asyncio
async def test_replay_completed_preflight_without_transaction():
    cmd = _command()
    fp = create_organization_request_fingerprint(cmd)
    stored = _stored_result()
    idempotency = _FakeIdempotencyStore(preflight=_completed_record(cmd, stored, fp))
    id_gen = MagicMock(side_effect=AssertionError("no debe generar UUID en replay"))
    handler = _build_handler(
        idempotency=idempotency,
        log=_CallLog(),
        session_sink=[],
        factory_capture=_FactoryCapture(),
        uow=_FakeUow(),
        id_generator=id_gen,
    )

    result = await handler.execute(cmd)

    assert result.tenant_id == OTHER_TENANT_ID
    assert result.idempotency_replayed is True
    id_gen.assert_not_called()
    assert idempotency.mark_completed_calls == 0


@pytest.mark.asyncio
async def test_same_key_different_fingerprint_rejected():
    cmd = _command()
    other = _command(display_name="Otro nombre")
    stored = _stored_result()
    record = _completed_record(cmd, stored, "sha-different-fingerprint")
    idempotency = _FakeIdempotencyStore(preflight=record)

    handler = _build_handler(
        idempotency=idempotency,
        log=_CallLog(),
        session_sink=[],
        factory_capture=_FactoryCapture(),
        uow=_FakeUow(),
        id_generator=lambda: TENANT_ID,
    )

    with pytest.raises(IdempotencyPayloadConflictError):
        await handler.execute(other)


@pytest.mark.asyncio
async def test_preflight_pending_raises_in_progress():
    cmd = _command()
    fp = create_organization_request_fingerprint(cmd)
    pending = IdempotencyRecord(
        operation=CREATE_ORGANIZATION_OPERATION,
        idempotency_key=cmd.idempotency_key,
        status=IdempotencyRecordStatus.PENDING,
        request_fingerprint=fp,
        tenant_id=TENANT_ID,
        branch_id=BRANCH_ID,
    )
    handler = _build_handler(
        idempotency=_FakeIdempotencyStore(preflight=pending),
        log=_CallLog(),
        session_sink=[],
        factory_capture=_FactoryCapture(),
        uow=_FakeUow(),
        id_generator=lambda: TENANT_ID,
    )
    with pytest.raises(IdempotencyInProgressError):
        await handler.execute(cmd)


@pytest.mark.asyncio
async def test_concurrent_reserve_already_completed_replays():
    cmd = _command()
    fp = create_organization_request_fingerprint(cmd)
    stored = _stored_result()
    idempotency = _FakeIdempotencyStore(
        reserve_raises=IdempotencyAlreadyCompletedError("done"),
        second_find=_completed_record(cmd, stored, fp),
    )
    ids = iter([TENANT_ID, BRANCH_ID])
    handler = _build_handler(
        idempotency=idempotency,
        log=_CallLog(),
        session_sink=[],
        factory_capture=_FactoryCapture(),
        uow=_FakeUow(),
        id_generator=lambda: next(ids),
    )

    result = await handler.execute(cmd)

    assert result.idempotency_replayed is True
    assert result.tenant_id == OTHER_TENANT_ID
    assert idempotency.find_calls == 2


@pytest.mark.asyncio
async def test_error_before_commit_skips_mark_completed():
    log = _CallLog()
    sessions: list[object | None] = []

    class _FailingBranchRepo(_RecordingBranchRepo):
        async def insert(self, branch: object, *, session: object | None = None) -> None:
            await super().insert(branch, session=session)
            raise RuntimeError("branch insert failed")

    capture = _FactoryCapture()
    failing_repo = _FailingBranchRepo(log, sessions)
    idempotency = _FakeIdempotencyStore(log=log)
    handler = _build_handler(
        idempotency=idempotency,
        log=log,
        session_sink=sessions,
        factory_capture=capture,
        uow=_FakeUow(log=log),
        id_generator=iter([TENANT_ID, BRANCH_ID]).__next__,
        branch_repo=failing_repo,
    )

    with pytest.raises(RuntimeError, match="branch insert failed"):
        await handler.execute(_command())

    assert idempotency.mark_completed_calls == 0


@pytest.mark.asyncio
async def test_uncertain_commit_recovers_completed_record():
    cmd = _command()
    fp = create_organization_request_fingerprint(cmd)
    stored = _stored_result()
    idempotency = _FakeIdempotencyStore(
        second_find=_completed_record(cmd, stored, fp),
    )
    ids = iter([TENANT_ID, BRANCH_ID])
    uow = _FakeUow(exit_error=MongoTransactionCommitUncertainError("uncertain"))
    handler = _build_handler(
        idempotency=idempotency,
        log=_CallLog(),
        session_sink=[],
        factory_capture=_FactoryCapture(),
        uow=uow,
        id_generator=lambda: next(ids),
    )

    result = await handler.execute(cmd)

    assert result.idempotency_replayed is True
    assert idempotency.find_calls == 2


@pytest.mark.asyncio
async def test_uncertain_commit_without_verifiable_result():
    idempotency = _FakeIdempotencyStore(second_find=None)
    ids = iter([TENANT_ID, BRANCH_ID])
    uow = _FakeUow(exit_error=MongoTransactionCommitUncertainError("uncertain"))
    handler = _build_handler(
        idempotency=idempotency,
        log=_CallLog(),
        session_sink=[],
        factory_capture=_FactoryCapture(),
        uow=uow,
        id_generator=lambda: next(ids),
    )

    with pytest.raises(OrganizationCommitUncertainError):
        await handler.execute(_command())


@pytest.mark.asyncio
async def test_recovery_paths_do_not_call_id_generator_again():
    cmd = _command()
    fp = create_organization_request_fingerprint(cmd)
    stored = _stored_result()
    id_gen = MagicMock(side_effect=[TENANT_ID, BRANCH_ID])
    idempotency = _FakeIdempotencyStore(
        reserve_raises=IdempotencyAlreadyCompletedError("done"),
        second_find=_completed_record(cmd, stored, fp),
    )
    handler = _build_handler(
        idempotency=idempotency,
        log=_CallLog(),
        session_sink=[],
        factory_capture=_FactoryCapture(),
        uow=_FakeUow(),
        id_generator=id_gen,
    )
    await handler.execute(cmd)
    assert id_gen.call_count == 2


@pytest.mark.asyncio
async def test_branch_factory_scopes_allowed_branch_id():
    capture = _FactoryCapture()
    ids = iter([TENANT_ID, BRANCH_ID])
    handler = _build_handler(
        idempotency=_FakeIdempotencyStore(),
        log=_CallLog(),
        session_sink=[],
        factory_capture=capture,
        uow=_FakeUow(),
        id_generator=lambda: next(ids),
    )
    await handler.execute(_command(created_by_user_id=USER_A_ID))

    assert capture.kwargs is not None
    assert capture.kwargs["tenant_id"] == TENANT_ID
    assert capture.kwargs["allowed_branch_id"] == BRANCH_ID
    assert capture.kwargs["actor_user_id"] == USER_A_ID
    assert capture.kwargs["actor_membership_id"] == CREATE_ORGANIZATION_BOOTSTRAP_MEMBERSHIP_ID


@pytest.mark.asyncio
async def test_bootstrap_actor_when_creator_missing():
    capture = _FactoryCapture()
    ids = iter([TENANT_ID, BRANCH_ID])
    handler = _build_handler(
        idempotency=_FakeIdempotencyStore(),
        log=_CallLog(),
        session_sink=[],
        factory_capture=capture,
        uow=_FakeUow(),
        id_generator=lambda: next(ids),
    )
    await handler.execute(_command())

    assert capture.kwargs is not None
    assert capture.kwargs["actor_user_id"] == CREATE_ORGANIZATION_BOOTSTRAP_USER_ID


def test_handler_source_has_no_direct_collection_access():
    source = HANDLER_SOURCE.read_text(encoding="utf-8")
    assert "Collection" not in source
    assert "insert_one" not in source
    assert "update_one" not in source
    assert "pymongo" not in source.lower()

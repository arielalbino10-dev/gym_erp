"""Sucursales operativas gym (H3-B.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from gym_erp_api.modules.access.domain.gym_permission import GymPermission
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.organization.application.commands.gym_branch_commands import (
    CreateAuthorizedBranchCommand,
)
from gym_erp_api.modules.organization.application.errors import (
    BranchDuplicateApplicationError,
    BranchNotFoundApplicationError,
)
from gym_erp_api.presentation.api_v1.gym.schemas.branches import (
    BranchListResponse,
    BranchResponse,
    CreateBranchRequest,
)
from gym_erp_api.presentation.auth.gym_context import (
    GymRequestContext,
    require_access_infrastructure,
)
from gym_erp_api.presentation.auth.gym_permissions import (
    require_gym_branch_read,
    require_gym_permission,
)
from gym_erp_api.presentation.http_security.csrf import csrf_binding_for_session
from gym_erp_api.presentation.http_security.dependencies import (
    enforce_cookie_session_mutation_security,
)

router = APIRouter(prefix="/branches", tags=["gym-branches"])


def _branch_response(view) -> BranchResponse:
    return BranchResponse(
        branch_id=view.branch_id,
        name=view.name,
        status=view.status,
        timezone=view.timezone,
        code=view.code,
    )


async def _enforce_gym_mutation_csrf(request: Request, gym_ctx: GymRequestContext) -> None:
    binding = csrf_binding_for_session(
        session_kind=SessionKind.GYM.value,
        session_id=gym_ctx.resolved_session.session.session_id,
    )
    await enforce_cookie_session_mutation_security(request, csrf_binding_key=binding)


@router.post("/", status_code=201)
async def create_branch(
    body: CreateBranchRequest,
    request: Request,
    gym_ctx: GymRequestContext = Depends(require_gym_permission(GymPermission.BRANCHES_CREATE)),
) -> JSONResponse:
    await _enforce_gym_mutation_csrf(request, gym_ctx)
    access = require_access_infrastructure(request)
    try:
        created = await access.create_authorized_branch.execute(
            tenant=gym_ctx.tenant,
            command=CreateAuthorizedBranchCommand(
                name=body.name,
                timezone=body.timezone,
                code=body.code,
            ),
        )
    except BranchDuplicateApplicationError:
        return JSONResponse(status_code=409, content={"detail": "Conflicto al crear sucursal."})
    payload = _branch_response(created)
    return JSONResponse(status_code=201, content=payload.model_dump())


@router.get("/")
async def list_branches(
    request: Request,
    gym_ctx: GymRequestContext = Depends(require_gym_branch_read()),
) -> JSONResponse:
    access = require_access_infrastructure(request)
    rows = await access.list_authorized_branches.execute(tenant=gym_ctx.tenant)
    payload = BranchListResponse(branches=[_branch_response(row) for row in rows])
    return JSONResponse(content=payload.model_dump())


@router.get("/{branch_id}")
async def get_branch(
    branch_id: str,
    request: Request,
    gym_ctx: GymRequestContext = Depends(require_gym_branch_read()),
) -> JSONResponse:
    access = require_access_infrastructure(request)
    try:
        row = await access.get_authorized_branch.execute(
            tenant=gym_ctx.tenant,
            branch_id=branch_id,
        )
    except BranchNotFoundApplicationError:
        return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado."})
    return JSONResponse(content=_branch_response(row).model_dump())

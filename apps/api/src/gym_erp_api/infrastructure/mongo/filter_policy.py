"""Política estricta de filtros y escrituras MongoDB (scope tenant / sucursal)."""

from __future__ import annotations

import copy
from typing import Any

from gym_erp_api.shared_kernel.exceptions import ForbiddenMongoOperatorError, TenantScopeError
from gym_erp_api.shared_kernel.tenant_context import TenantContext

PROTECTED_FIELD_KEYS = frozenset({"tenant_id"})
BRANCH_PROTECTED_KEYS = frozenset({"branch_id"})

MAX_AGGREGATION_EXPRESSION_DEPTH = 8

FORBIDDEN_FILTER_ROOT_OPERATORS = frozenset(
    {
        "$where",
        "$expr",
        "$or",
        "$and",
        "$nor",
        "$jsonSchema",
        "$text",
        "$function",
    }
)

ALLOWED_FIELD_OPERATORS = frozenset(
    {
        "$eq",
        "$ne",
        "$gt",
        "$gte",
        "$lt",
        "$lte",
        "$in",
        "$nin",
        "$exists",
    }
)

ALLOWED_UPDATE_TOP_OPERATORS = frozenset({"$set", "$unset", "$inc", "$push", "$pull"})

ALLOWED_AGGREGATION_STAGES = frozenset(
    {
        "$match",
        "$project",
        "$group",
        "$sort",
        "$limit",
        "$skip",
        "$count",
        "$unwind",
    }
)

FORBIDDEN_AGGREGATION_STAGES = frozenset(
    {
        "$lookup",
        "$graphLookup",
        "$out",
        "$merge",
        "$unionWith",
        "$facet",
        "$bucket",
        "$bucketAuto",
    }
)

ALLOWED_AGGREGATION_EXPRESSION_OPERATORS = frozenset(
    {
        "$sum",
        "$avg",
        "$min",
        "$max",
        "$first",
        "$last",
        "$push",
        "$addToSet",
        "$literal",
        "$size",
        "$ifNull",
    }
)


def _deepcopy(value: Any) -> Any:
    return copy.deepcopy(value)


def require_business_filter(sanitized_user_filter: dict[str, Any]) -> None:
    """Exige al menos un criterio de negocio además del tenant (mutaciones)."""
    if not sanitized_user_filter:
        raise TenantScopeError("Se requiere al menos un criterio de negocio además del tenant.")


def _field_path_touches_protected(field_path: str, protected: frozenset[str]) -> bool:
    if field_path in protected:
        return True
    return any(segment in protected for segment in field_path.split("."))


def _reject_protected_keys(
    document: dict[str, Any],
    *,
    context: str,
    extra_protected: frozenset[str] = frozenset(),
) -> None:
    protected = PROTECTED_FIELD_KEYS | extra_protected
    for key in document:
        if _field_path_touches_protected(key, protected):
            raise TenantScopeError(f"No se permite modificar {key!r} en {context}.")


def _validate_field_operator_value(op: str, value: Any) -> None:
    if op in ("$in", "$nin"):
        if not isinstance(value, (list, tuple)):
            raise ForbiddenMongoOperatorError(f"{op} requiere una lista.")
        return
    if op == "$exists":
        if not isinstance(value, bool):
            raise ForbiddenMongoOperatorError("$exists requiere un booleano.")
        return
    if op in ("$eq", "$ne", "$gt", "$gte", "$lt", "$lte"):
        return
    raise ForbiddenMongoOperatorError(f"Operador de campo no permitido: {op!r}.")


def _sanitize_filter_value(value: Any, *, path: str) -> Any:
    if isinstance(value, dict):
        return _sanitize_filter_document(value, path=path, allow_root_operators=False)
    if isinstance(value, list):
        return [_sanitize_filter_value(item, path=f"{path}[]") for item in value]
    return value


def _sanitize_filter_document(
    document: dict[str, Any],
    *,
    path: str,
    allow_root_operators: bool,
) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise TenantScopeError(f"El filtro en {path} debe ser un documento.")

    sanitized: dict[str, Any] = {}
    for key, value in document.items():
        if not isinstance(key, str):
            raise TenantScopeError(f"Clave de filtro inválida en {path}.")
        if key.startswith("$"):
            if not allow_root_operators:
                raise ForbiddenMongoOperatorError(f"Operador {key!r} no permitido en {path}.")
            if key in FORBIDDEN_FILTER_ROOT_OPERATORS:
                raise ForbiddenMongoOperatorError(f"Operador prohibido: {key!r}.")
            raise ForbiddenMongoOperatorError(f"Operador desconocido o no validable: {key!r}.")
        if key in PROTECTED_FIELD_KEYS:
            raise TenantScopeError(f"No se permite filtrar por {key!r} desde capas superiores.")
        if isinstance(value, dict) and any(k.startswith("$") for k in value):
            op_doc: dict[str, Any] = {}
            for op, op_val in value.items():
                if not op.startswith("$"):
                    raise ForbiddenMongoOperatorError(f"Clave mixta no permitida en {path}.{key}.")
                if op not in ALLOWED_FIELD_OPERATORS:
                    raise ForbiddenMongoOperatorError(f"Operador de campo prohibido: {op!r}.")
                _validate_field_operator_value(op, op_val)
                op_doc[op] = _sanitize_filter_value(op_val, path=f"{path}.{key}{op}")
            sanitized[key] = op_doc
        else:
            sanitized[key] = _sanitize_filter_value(value, path=f"{path}.{key}")
    return sanitized


def sanitize_user_filter(user_filter: dict[str, Any] | None) -> dict[str, Any]:
    """Copia y valida un filtro libre (sin mutar la entrada)."""
    if user_filter is None:
        return {}
    if not isinstance(user_filter, dict):
        raise TenantScopeError("El filtro debe ser un documento.")
    copied = _deepcopy(user_filter)
    return _sanitize_filter_document(copied, path="filter", allow_root_operators=False)


def sanitize_branch_scoped_user_filter(user_filter: dict[str, Any] | None) -> dict[str, Any]:
    """Como sanitize_user_filter pero rechaza branch_id del caller."""
    sanitized = sanitize_user_filter(user_filter)
    if "branch_id" in sanitized:
        raise TenantScopeError("No se permite filtrar por branch_id en colecciones branch-scoped.")
    return sanitized


def _sanitize_user_part(
    user_filter: dict[str, Any] | None,
    *,
    branch_scoped: bool,
) -> dict[str, Any]:
    if branch_scoped:
        return sanitize_branch_scoped_user_filter(user_filter)
    return sanitize_user_filter(user_filter)


def build_scoped_filter(
    ctx: TenantContext,
    user_filter: dict[str, Any] | None,
    *,
    branch_scoped: bool,
) -> dict[str, Any]:
    """Construye filtro con tenant_id confiable (índice no sustituye este filtro)."""
    sanitized = _sanitize_user_part(user_filter, branch_scoped=branch_scoped)
    scoped: dict[str, Any] = {"tenant_id": ctx.tenant_id}
    if branch_scoped and ctx.allowed_branch_ids is not None:
        scoped["branch_id"] = {"$in": list(ctx.allowed_branch_ids)}
    if sanitized:
        scoped = {**scoped, **sanitized}
    return scoped


def _assert_trusted_branch_id_in_scope(
    ctx: TenantContext,
    branch_id: str,
    *,
    branch_scoped: bool,
) -> None:
    del branch_scoped
    if not isinstance(branch_id, str) or not branch_id:
        raise TenantScopeError("branch_id debe ser una cadena no vacía.")
    if ctx.allowed_branch_ids is not None and branch_id not in ctx.allowed_branch_ids:
        raise TenantScopeError("branch_id fuera del alcance permitido por el contexto.")


def build_trusted_branch_id_read_filter(
    ctx: TenantContext,
    branch_id: str,
    *,
    branch_scoped: bool,
) -> dict[str, Any]:
    """Lectura por branch_id desde capa repositorio (no sustituye filtros libres del caller)."""
    _assert_trusted_branch_id_in_scope(ctx, branch_id, branch_scoped=branch_scoped)
    return {"tenant_id": ctx.tenant_id, "branch_id": branch_id}


def build_trusted_branch_id_mutation_filter(
    ctx: TenantContext,
    branch_id: str,
    *,
    branch_scoped: bool,
) -> dict[str, Any]:
    """Mutación por branch_id desde capa repositorio."""
    _assert_trusted_branch_id_in_scope(ctx, branch_id, branch_scoped=branch_scoped)
    return {"tenant_id": ctx.tenant_id, "branch_id": branch_id}


def build_mutation_scoped_filter(
    ctx: TenantContext,
    user_filter: dict[str, Any] | None,
    *,
    branch_scoped: bool,
) -> dict[str, Any]:
    """Filtro para update/delete: tenant + criterio de negocio obligatorio."""
    sanitized = _sanitize_user_part(user_filter, branch_scoped=branch_scoped)
    require_business_filter(sanitized)
    scoped: dict[str, Any] = {"tenant_id": ctx.tenant_id}
    if branch_scoped and ctx.allowed_branch_ids is not None:
        scoped["branch_id"] = {"$in": list(ctx.allowed_branch_ids)}
    if sanitized:
        scoped = {**scoped, **sanitized}
    return scoped


def _validate_branch_id_for_write(
    branch_id: str,
    ctx: TenantContext,
    *,
    branch_scoped: bool,
) -> None:
    if not branch_scoped or ctx.allowed_branch_ids is None:
        return
    if branch_id not in ctx.allowed_branch_ids:
        raise TenantScopeError("branch_id fuera del alcance permitido por el contexto.")


def _sanitize_update_document(
    update: dict[str, Any],
    *,
    path: str,
) -> dict[str, Any]:
    if not isinstance(update, dict):
        raise TenantScopeError("La actualización debe ser un documento con operadores.")
    if not update:
        raise TenantScopeError("La actualización no puede estar vacía.")

    sanitized: dict[str, Any] = {}
    for op, payload in update.items():
        if not op.startswith("$"):
            raise TenantScopeError("Actualización por reemplazo de documento no permitida en H1-B.")
        if op not in ALLOWED_UPDATE_TOP_OPERATORS:
            raise ForbiddenMongoOperatorError(f"Operador de escritura no permitido: {op!r}.")
        if not isinstance(payload, dict):
            raise TenantScopeError(f"El payload de {op} debe ser un documento.")
        payload_copy = _deepcopy(payload)
        _reject_protected_keys(
            payload_copy,
            context=f"actualización {op}",
            extra_protected=BRANCH_PROTECTED_KEYS,
        )
        if op == "$unset":
            protected = PROTECTED_FIELD_KEYS | BRANCH_PROTECTED_KEYS
            for key in payload_copy:
                if _field_path_touches_protected(key, protected):
                    raise TenantScopeError(f"No se puede $unset {key!r}.")
        sanitized[op] = payload_copy
    return sanitized


def sanitize_update(update: dict[str, Any], *, branch_scoped: bool = False) -> dict[str, Any]:
    """Valida operadores de actualización (sin pipeline ni replace).

    ``branch_scoped`` se conserva en la firma por compatibilidad con el repositorio;
    ``tenant_id`` y ``branch_id`` son inmutables en updates genéricos en ambos modos.
    """
    del branch_scoped
    if isinstance(update, list):
        raise ForbiddenMongoOperatorError("Actualizaciones por pipeline no permitidas en H1-B.")
    copied = _deepcopy(update)
    return _sanitize_update_document(copied, path="update")


def prepare_insert_document(
    document: dict[str, Any],
    ctx: TenantContext,
    *,
    branch_scoped: bool = False,
) -> dict[str, Any]:
    """Copia el documento e impone tenant_id confiable."""
    if not isinstance(document, dict):
        raise TenantScopeError("El documento a insertar debe ser un dict.")
    copied = _deepcopy(document)
    existing = copied.get("tenant_id")
    if existing is not None and existing != ctx.tenant_id:
        raise TenantScopeError("tenant_id del documento no coincide con el contexto.")
    copied["tenant_id"] = ctx.tenant_id
    if branch_scoped:
        branch_id = copied.get("branch_id")
        if branch_id is None:
            raise TenantScopeError("branch_id obligatorio en colección branch-scoped.")
        _validate_branch_id_for_write(str(branch_id), ctx, branch_scoped=True)
    return copied


def prepare_insert_many(
    documents: list[dict[str, Any]],
    ctx: TenantContext,
    *,
    branch_scoped: bool = False,
) -> list[dict[str, Any]]:
    return [prepare_insert_document(doc, ctx, branch_scoped=branch_scoped) for doc in documents]


def _validate_mongo_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ForbiddenMongoOperatorError(f"{name} requiere un entero.")
    if value < 0:
        raise ForbiddenMongoOperatorError(f"{name} no puede ser negativo.")
    return value


def _validate_field_path(value: Any, *, path: str) -> str:
    if not isinstance(value, str):
        raise ForbiddenMongoOperatorError(f"Referencia de campo inválida en {path}.")
    if value.startswith("$$"):
        raise ForbiddenMongoOperatorError(f"Referencia de sistema prohibida en {path}.")
    if value.startswith("$"):
        return value
    raise ForbiddenMongoOperatorError(f"Se esperaba ruta de campo con '$' en {path}.")


def _sanitize_aggregation_expression(
    value: Any,
    *,
    path: str,
    depth: int = 0,
) -> Any:
    if depth > MAX_AGGREGATION_EXPRESSION_DEPTH:
        raise ForbiddenMongoOperatorError(f"Expresión demasiado profunda en {path}.")

    if isinstance(value, str):
        if value.startswith("$"):
            return _validate_field_path(value, path=path)
        return value
    if value is None or isinstance(value, float):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return [
            _sanitize_aggregation_expression(item, path=f"{path}[]", depth=depth + 1)
            for item in value
        ]
    if isinstance(value, dict):
        if not value:
            return value
        if len(value) == 1:
            key = next(iter(value))
            if key.startswith("$"):
                if key not in ALLOWED_AGGREGATION_EXPRESSION_OPERATORS:
                    raise ForbiddenMongoOperatorError(
                        f"Operador de agregación no permitido: {key!r} en {path}."
                    )
                inner = value[key]
                return {
                    key: _sanitize_aggregation_expression(
                        inner,
                        path=f"{path}.{key}",
                        depth=depth + 1,
                    )
                }
        sanitized_doc: dict[str, Any] = {}
        for key, inner in value.items():
            if not isinstance(key, str):
                raise ForbiddenMongoOperatorError(f"Clave inválida en expresión {path}.")
            if key.startswith("$"):
                raise ForbiddenMongoOperatorError(
                    f"Operador de agregación no permitido: {key!r} en {path}."
                )
            sanitized_doc[key] = _sanitize_aggregation_expression(
                inner,
                path=f"{path}.{key}",
                depth=depth + 1,
            )
        return sanitized_doc
    raise ForbiddenMongoOperatorError(f"Tipo no permitido en expresión de agregación: {path}.")


def _sanitize_group_stage(payload: dict[str, Any]) -> dict[str, Any]:
    if "_id" not in payload:
        raise TenantScopeError("$group requiere campo '_id'.")
    sanitized = _deepcopy(payload)
    sanitized["_id"] = _sanitize_aggregation_expression(
        sanitized["_id"],
        path="$group._id",
    )
    for key, value in list(sanitized.items()):
        if key == "_id":
            continue
        sanitized[key] = _sanitize_aggregation_expression(value, path=f"$group.{key}")
    return sanitized


def _sanitize_project_stage(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = _deepcopy(payload)
    for key, value in sanitized.items():
        if not isinstance(key, str):
            raise ForbiddenMongoOperatorError("Claves de $project deben ser cadenas.")
        if key.startswith("$"):
            raise ForbiddenMongoOperatorError(f"Clave no permitida en $project: {key!r}.")
        if value in (0, 1, True, False):
            if value not in (0, 1):
                raise ForbiddenMongoOperatorError("$project solo admite 0 o 1 como inclusion.")
            continue
        sanitized[key] = _sanitize_aggregation_expression(value, path=f"$project.{key}")
    return sanitized


def _sanitize_sort_stage(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = _deepcopy(payload)
    for key, value in sanitized.items():
        if not isinstance(key, str) or key.startswith("$"):
            raise ForbiddenMongoOperatorError("Claves de $sort inválidas.")
        if isinstance(value, bool) or value not in (1, -1):
            raise ForbiddenMongoOperatorError("$sort requiere 1 o -1 (entero).")
    return sanitized


def _sanitize_unwind_stage(payload: Any) -> Any:
    if isinstance(payload, str):
        return _validate_field_path(payload, path="$unwind")
    raise ForbiddenMongoOperatorError("$unwind debe ser una ruta de campo en cadena.")


def _sanitize_count_stage(payload: Any) -> str:
    if not isinstance(payload, str) or not payload:
        raise ForbiddenMongoOperatorError("$count requiere un nombre de campo de salida.")
    return payload


def _sanitize_aggregation_match(match_doc: dict[str, Any]) -> dict[str, Any]:
    return sanitize_user_filter(match_doc)


def sanitize_aggregation_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Valida etapas de agregación (lista blanca mínima)."""
    if not isinstance(stages, list):
        raise TenantScopeError("El pipeline debe ser una lista.")
    sanitized_stages: list[dict[str, Any]] = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict) or len(stage) != 1:
            raise TenantScopeError(f"Etapa {index} inválida: debe ser un documento de una clave.")
        stage_name = next(iter(stage))
        if stage_name in FORBIDDEN_AGGREGATION_STAGES:
            raise ForbiddenMongoOperatorError(f"Etapa de agregación prohibida: {stage_name!r}.")
        if stage_name not in ALLOWED_AGGREGATION_STAGES:
            raise ForbiddenMongoOperatorError(f"Etapa de agregación no permitida: {stage_name!r}.")
        payload = _deepcopy(stage[stage_name])
        if stage_name == "$match":
            if not isinstance(payload, dict):
                raise TenantScopeError("$match debe ser un documento.")
            payload = _sanitize_aggregation_match(payload)
        elif stage_name == "$group":
            if not isinstance(payload, dict):
                raise TenantScopeError("$group debe ser un documento.")
            payload = _sanitize_group_stage(payload)
        elif stage_name == "$project":
            if not isinstance(payload, dict):
                raise TenantScopeError("$project debe ser un documento.")
            payload = _sanitize_project_stage(payload)
        elif stage_name == "$sort":
            if not isinstance(payload, dict):
                raise TenantScopeError("$sort debe ser un documento.")
            payload = _sanitize_sort_stage(payload)
        elif stage_name == "$limit":
            payload = _validate_mongo_int("$limit", payload)
        elif stage_name == "$skip":
            payload = _validate_mongo_int("$skip", payload)
        elif stage_name == "$count":
            payload = _sanitize_count_stage(payload)
        elif stage_name == "$unwind":
            payload = _sanitize_unwind_stage(payload)
        sanitized_stages.append({stage_name: payload})
    return sanitized_stages


def build_aggregation_pipeline(
    ctx: TenantContext,
    stages: list[dict[str, Any]],
    *,
    branch_scoped: bool,
) -> list[dict[str, Any]]:
    """Prefija $match obligatorio y valida etapas."""
    sanitized = sanitize_aggregation_stages(stages)
    mandatory_match = build_scoped_filter(ctx, None, branch_scoped=branch_scoped)
    return [{"$match": mandatory_match}, *sanitized]

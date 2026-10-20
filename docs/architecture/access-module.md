# Módulo Access (H2-C.2)

Autorización multi-tenant en **gym_platform**: membresías usuario–tenant, roles gym mínimos y
construcción de `TenantContext` confiable. **Sin endpoints HTTP** ni CRUD operational en esta fase.

Referencias: [ADR-0002](../adr/0002-aislamiento-multiempresa.md), [ADR-0003](../adr/0003-autenticacion-sesiones.md)
(Accepted), [ADR-0008](../adr/0008-dos-bases-mongodb-platform-operational.md),
[ADR-0009](../adr/0009-modelo-organizacional-mvp.md), diseño [H2-C.1](tenant-context-and-repositories.md).

## TenantMembership

| Campo | Descripción |
|-------|-------------|
| `membership_id` | UUID v4 (PK lógica, `_id` Mongo) |
| `user_id` / `tenant_id` | Par canónico usuario–empresa |
| `status` | `invited`, `active`, `suspended`, `revoked` |
| `branch_scope_mode` | `all_branches` \| `explicit_branches` |
| `allowed_branch_ids` | Solo si explícito; vacío prohibido en `active` |
| `gym_roles` | Subconjunto de `gym_owner`, `gym_admin`, `branch_admin` |
| `authz_epoch` | Entero; incremento en cambios de estado, rol o alcance |
| Auditoría | `created_at`, `updated_at`, `invited_at`, `accepted_at`, `created_by_user_id` |

Distinto de **socio** (`member`) en gym_operational y de **platform_operator_eligibilities** (consola SaaS pre-RBAC).

## Decisión de unicidad (H2-C.2)

**Estrategia A — documento canónico por `(tenant_id, user_id)`:**

- Índice único compuesto `{ tenant_id: 1, user_id: 1 }` (sin índice parcial).
- Historia vía `status` y timestamps, no filas duplicadas.
- Reactivación: transición `revoked → invited → active` o `suspended → active` con `authz_epoch++`.
- Idempotencia de alta: `DuplicateKeyError` → tratar como membresía existente en capa application (H2-C.3+).

**Descartada estrategia B** (único parcial solo `active`): más documentos por par, complejidad en reactivación y auditoría MVP.

## Roles gym mínimos

| Rol | Alcance típico |
|-----|----------------|
| `gym_owner` | Tenant completo |
| `gym_admin` | Operación multi-sucursal |
| `branch_admin` | Requiere `explicit_branches` y lista no vacía |

**No** incluye `root_admin` ni `platform_admin` (futuro `platform_role_assignments`).

Permisos atómicos y motor RBAC: **H2-C.4+**.

## TenantContextFactory

Entrada: `TrustedGymAuthContext(user_id, selected_tenant_id)` — identidad ya validada por identity.

1. Sin `selected_tenant_id` → `TenantNotSelectedError` (distinto de acceso denegado).
2. Carga membresía canónica por par usuario–tenant.
3. Exige `status=active`; suspendida/revocada/invited → `MembershipAccessDeniedError`.
4. Carga tenant platform; `TenantOperationalPolicy.ensure_allows_operational`.
5. Deriva `allowed_branch_ids` para `TenantContext` (`None` = all_branches).

**No** lee roles ni tenant desde el cliente.

## Relación con AuthSession

- `AuthSession.active_tenant_id` (gym) es **hint de selección** persistido en sesión (H2-C.3).
- Autorización efectiva **siempre** revalida membresía + tenant + epoch en factory.
- Cambio material de membresía incrementa `authz_epoch`; sesión puede comparar hint en H2-C.3.

## Revocación y reinvitación (H2-C.2.1)

- `revoke()` → `status=revoked`, `authz_epoch++`.
- **No** existe `reinvite()` implícito: una membresía revocada **no** recupera roles ni sucursales anteriores.
- Nuevo acceso: `apply_reinvite_grant(...)` con **roles y alcance explícitos** → `invited` → `accept_invitation()` → `active`.
- `reactivate()` solo desde `suspended` (membresía ya aceptada antes).
- Factory rechaza `revoked`, `invited` y `suspended`.

## Alcance de sucursales (H2-C.2.1)

- El dominio valida UUID y coherencia rol/alcance; **no** comprueba pertenencia en operational.
- Antes de insertar o cambiar `allowed_branch_ids`, la capa application debe llamar
  `ensure_membership_branch_scope` con un `TenantBranchScopeValidator`.
- Adaptador `OrganizationBranchScopeValidator`: `tenant_id → BranchRepository` scoped (lectura operational).
- La **TenantContextFactory** no consulta operational; solo refleja lo persistido en platform tras validación previa.
- Un `branch_id` válido como UUID **no** implica autorización sin membresía activa y validación de pertenencia al grant.

## Persistencia

| Colección | Base | Índices |
|-----------|------|---------|
| `tenant_memberships` | gym_platform | `uniq_tenant_user`, `idx_user_status`, `idx_tenant_status` |

Implementación: `MongoTenantMembershipRepository`, índices en `access_index_specs.py`.
Actualizaciones con **OCC por `authz_epoch`** y `replace_one` (documento completo) para evitar
campos obsoletos en Mongo. Tests de integración usan prefijo `gym_erp_acc_mem_`.

## H2-C.3 (dependencias)

- `POST /gym/auth/select-tenant` y ampliar `GET /gym/auth/session`.
- Dependencia FastAPI `require_gym_tenant_context`.
- Comparación `authz_epoch` sesión vs membresía.
- Casos de uso de alta/revoke membresía (sin CRUD negocio operational).

## Controles

- Unit: dominio, factory (mocks), transiciones, roles gym vs platform.
- Integración: round-trip Mongo, duplicado, OCC, listado multi-tenant.
- Reutilizar matriz [tenant-isolation](tenant-isolation-test-matrix.md) al conectar HTTP.

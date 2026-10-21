# Módulo Organization (H1-D)

Documentación del módulo **`gym_erp_api.modules.organization`**: dominio Tenant/Sucursal,
persistencia platform/operational, políticas internas, transacciones multi-base e
idempotencia para el alta interna **CreateOrganization**.

**Estado:** implementado en backend (sin endpoints HTTP organization). Autenticación HTTP en
[ADR-0003](../adr/0003-autenticacion-sesiones.md) (**Accepted**); RBAC gym en módulo
[access](access-module.md) (H2-C.2+).

Referencias: [ADR-0008](../adr/0008-dos-bases-mongodb-platform-operational.md),
[ADR-0009](../adr/0009-modelo-organizacional-mvp.md),
[ADR-0010](../adr/0010-organization-onboarding-idempotencia.md) (decisiones H1-D, **Proposed**).

---

## Responsabilidades

| Capa | Responsabilidad |
|------|-----------------|
| **domain** | Entidades `Tenant`, `Branch`; enums; validadores; VOs (`BranchAddress`). |
| **application** | Comandos/resultados; fingerprint; puertos; políticas y scopes internos; **CreateOrganizationHandler**. |
| **infrastructure/mongo** | Mappers BSON; repos platform (tenant, idempotency); repo operational (branch vía scope). |
| **presentation** | **No implementada** en H1-D (prohibido exponer HTTP sin auth — ver § Seguridad). |

El módulo **no** sustituye `TenantScopedRepository` ni accede a operational sin contexto
de tenant válido.

---

## Separación platform / operational

| Base (ref.) | Contenido organization (H1-D) |
|-------------|----------------------------------|
| **gym_platform** | Documentos de **tenant** (estado `provisioning` → `active`). Registros de **idempotencia** de provisioning (`organization_provisioning_idempotency` como nombre lógico de colección en producción; tests usan prefijos efímeros). |
| **gym_operational** | Documentos de **sucursal** (`branch`) con `tenant_id` + `branch_id`. |

Un único `AsyncMongoClient` y `MongoDatabases` acceden a ambas bases (ADR-0008). Las
escrituras coordinated del alta usan **MongoUnitOfWork** (misma sesión transaccional).

---

## Tenant y Branch

- **Tenant:** empresa cliente SaaS; alta inicial en `provisioning`, activación en la misma
  transacción que la primera sucursal.
- **Branch:** primera sucursal del tenant; siempre comparte `tenant_id` generado en
  application (no aceptado desde cliente).
- **Marca comercial (MVP):** campos del tenant (`display_name`, etc.) según ADR-0009; sin
  entidad `Brand` separada.

Identificadores: UUID v4 canónicos (`shared_kernel.identifiers`).

---

## Políticas de aislamiento

### Operational (H1-C + H1-D)

- Lecturas/escrituras de sucursales vía **`OperationalBranchRepository`** sobre
  **`TenantScopedRepository`**.
- En provisioning, el handler construye contexto con `allowed_branch_ids={branch_id}` y
  `branch_scoped=True` (factory inyectada; ver bootstrap en ADR-0010).
- Filtros **`build_trusted_branch_id_*`**: lookup/mutación por `branch_id` solo si el id
  está en el alcance del contexto.
- Inserción cross-tenant rechazada por validación de dominio + filtros scoped.

### Platform

- **`PlatformTenantRepository`:** `insert`, `get_by_id`, `exists_by_id`, `save` — **sin**
  listados globales.
- **`PlatformIdempotencyRepository`:** solo platform; sin acceso operational.

### Scopes internos (no autenticación)

- **`PlatformProvisioningScope`:** acota el `tenant_id` objetivo durante el alta; **no**
  reemplaza identidad ni roles (control organizativo de capa application).
- **`TenantOperationalPolicy` / `TenantMemberAccess`:** preparación para operaciones
  futuras con membership (H1-D.3.1).

---

## Casos de uso

| Caso de uso | Estado | Notas |
|-------------|--------|-------|
| **CreateOrganization** (interno) | **Implementado** | `CreateOrganizationHandler`; transacción + idempotencia. |
| HTTP POST /organizations | **Pendiente** | Requiere ADR-0003 + guard de rol platform. |
| CLI / jobs de provisioning | **Pendiente** | Mismo handler; wiring en composition root futuro. |
| Listado/admin global de tenants | **Fuera de alcance H1-D** | Sin API en repos platform. |
| Reconciliación automática commit incierto | **Pendiente** | Solo consulta idempotencia + error explícito hoy. |
| Membership real en bootstrap | **Pendiente** | UUID técnicos documentados en ADR-0010. |

Entrada del handler: **`CreateOrganizationCommand.build(...)`** (normalización y
`idempotency_key` validada).

---

## MongoUnitOfWork

Implementación: `gym_erp_api.infrastructure.mongo.mongo_unit_of_work`.

### Modelo

1. **Una sesión** PyMongo async por instancia de UoW (`start_session`).
2. **Una transacción** (`start_transaction`) que abarca operaciones en **platform y
   operational** del mismo replica set (mismo cliente).
3. Repositorios reciben `session=` opaco; `session_support` valida mismo cliente, sesión
   activa y, en escrituras scoped/idempotencia, **presencia en transacción**.

### Commit y abort

- Salida normal del `async with`: commit de la transacción.
- Excepción en el cuerpo: abort vía context manager de PyMongo (sin reintento automático
  del callback en este UoW).
- Instancia **no reutilizable** (`MongoUnitOfWorkInactiveError` tras consumo).

### Commits inciertos

- Etiqueta **`UnknownTransactionCommitResult`** →
  **`MongoTransactionCommitUncertainError`**.
- No se afirma rollback ni éxito; **CreateOrganizationHandler** consulta idempotencia
  con lectura independiente (sin sesión fallida) y devuelve replay o
  **`OrganizationCommitUncertainError`**.

### Limitaciones documentadas (deuda)

- **`max_commit_time_ms`** limita el comando `commitTransaction`, no toda la duración del
  bloque de negocio.
- **Sin** `readConcern` / `writeConcern("majority")` explícitos en `start_transaction`
  (depende de defaults del cliente; ver ADR-0010 y riesgos MEDIUM).
- **Sin** `with_transaction` del driver (sin reintentos automáticos de callback).

Errores de infraestructura: `infrastructure/mongo/uow_errors.py`.

---

## Idempotencia (CreateOrganization)

Puerto: `application/ports/idempotency_store.py`. Adaptador:
`PlatformIdempotencyRepository`.

### Namespace

- **Operación:** constante `CREATE_ORGANIZATION_OPERATION` (`create_organization`).
- **Clave de documento:** `_id = operation + U+001E + idempotency_key` (ver mapper).
- La **`idempotency_key`** la envía el cliente futuro; hoy solo tests e invocación interna.

### Fingerprint canónico

- SHA-256 sobre payload de negocio normalizado (versión v1, Unicode NFC).
- **No** incluye `tenant_id`/`branch_id` (se generan en servidor).
- **`created_by_user_id`** opcional entra en el hash cuando está presente.

### Flujo transaccional

1. **Preflight** `find` (sin sesión txn) → replay si `completed` + mismo fingerprint.
2. Generación **única** de `tenant_id` y `branch_id` antes de abrir UoW.
3. Dentro de UoW: **`reserve`** (pending) → inserts/activación → **`mark_completed`**.
4. Commit; resultado solo tras confirmación (salvo replay/commit incierto recuperable).

### Replay, conflictos e in-progress

| Situación | Comportamiento |
|-----------|----------------|
| Misma clave, mismo fingerprint, `completed` | Replay (`idempotency_replayed=True`). |
| Misma clave, fingerprint distinto | `IdempotencyPayloadConflictError`. |
| `pending` visible (raro fuera de txn ajena) | `IdempotencyInProgressError`. |
| `DuplicateKeyError` en `reserve` | Re-`find` sin sesión; distingue completed / conflict / in-progress. |
| `TransientTransactionError` en `reserve` | `IdempotencyInProgressError` (adaptador). |

### Riesgo: claves globales entre actores

El `_id` de idempotencia **no** incluye hoy actor ni tenant. Cualquier principal que
conozca la clave puede obtener replay del mismo resultado. Mitigación futura: incluir
principal autenticado en namespace o validar ownership en capa HTTP (ADR-0010, riesgo HIGH).

---

## Seguridad y exposición

- **Prohibido** exponer CreateOrganization (o repos platform sin guard) vía HTTP público
  **sin** autenticación y autorización de **rol platform** validada en backend (ADR-0003).
- **Prohibido** tomar `tenant_id` / `branch_id` del frontend para el alta inicial.
- **Prohibido** bypass de `TenantScopedRepository` para escrituras operational.
- Un **`TenantContext` válido en tests no implica usuario autenticado.**

Estado actual del API: solo health en `/api/v1` ([apps/api/README.md](../../apps/api/README.md)).

---

## Riesgos conocidos (auditoría H1-D)

### HIGH (antes de producción / endpoints)

| ID | Riesgo | Mitigación prevista |
|----|--------|---------------------|
| H1 | Handler invocable sin guard real de platform | Endpoint + RBAC backend; ADR-0003 Accepted. |
| H2 | Idempotencia global por clave (sin actor en `_id`) | Namespace con principal; política de replay. |

### MEDIUM

| ID | Riesgo | Notas |
|----|--------|-------|
| M1 | UoW sin read/write concern explícitos | Definir en infra antes de prod RS. |
| M2 | Errores PyMongo fuera de `reserve` no mapeados | Capa application/HTTP futura. |
| M3 | `tz_aware=True` global en cliente Mongo | Validar suites integración completas. |
| M4 | Bootstrap UUID fijos (`bootstrap_context.py`) | Membership real post ADR-0003. |
| M5–M6 | Cobertura integración sesión/concurrencia | Endurecer tests en iteraciones futuras. |

---

## Pruebas

| Tipo | Ubicación | CI |
|------|-----------|-----|
| Unitarias | `apps/api/tests/unit/modules/organization/` | **Sí** (`pytest -m "not integration"`) |
| Integración organization | `apps/api/tests/integration/organization/` | **No** (manual, MongoDB local) |

Ver [integration-mongodb.md](../development/integration-mongodb.md) § Organization.

---

## Mapa de código (referencia)

```text
apps/api/src/gym_erp_api/modules/organization/
├── domain/
├── application/
│   ├── commands/create_organization.py
│   ├── use_cases/create_organization_handler.py
│   ├── ports/
│   └── authorization/ | policies/
└── infrastructure/mongo/
    ├── platform_tenant_repository.py
    ├── operational_branch_repository.py
    └── platform_idempotency_repository.py

apps/api/src/gym_erp_api/infrastructure/mongo/
├── mongo_unit_of_work.py
├── session_support.py
└── scoped_repository.py
```

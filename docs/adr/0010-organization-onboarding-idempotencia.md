# ADR-0010: Onboarding organizacional transaccional e idempotencia (H1-D)

- **Estado:** Proposed
- **Fecha:** 2026-10-15 (cierre documentación H1-D.4)
- **Decisores:** Pendiente de aprobación del propietario del producto
- **Relacionado:** ADR-0008 (Accepted), ADR-0009 (Accepted), ADR-0003 (Proposed)

## Contexto

H1-D implementó el módulo **organization** con alta interna **CreateOrganization**:
tenant en platform, primera sucursal en operational, e idempotencia en platform, coordinados
por **MongoUnitOfWork**. No hay endpoints HTTP ni autenticación de plataforma (ADR-0003
sigue Proposed).

ADR-0008 ya prefería transacciones multi-base cortas e idempotencia como alternativa.
Este ADR **no modifica** ADR-0008/0009; registra decisiones **concretas** de H1-D y deuda
antes de producción.

## Decisión

### 1. Transacciones multi-base (mismo replica set)

1. Usar **`MongoUnitOfWork`**: una sesión, una transacción, participación de repos platform
   y operational con el mismo `session=`.
2. **No** reutilizar instancias de UoW ni sesiones cerradas.
3. **No** usar `ClientSession.with_transaction` con reintentos automáticos del driver en
   este UoW (control explícito en application para idempotencia).
4. Commits inciertos (`UnknownTransactionCommitResult`) se traducen a error de infra y
   reconciliación vía **lectura de idempotencia** en application, sin segunda alta con
   nuevos UUID.

**Pendiente (M1):** fijar `readConcern` / `writeConcern("majority")` en
`start_transaction` cuando se valide el clúster de producción.

### 2. Onboarding interno (CreateOrganization)

1. Caso de uso **`CreateOrganizationHandler`** como **API interna** (application), no HTTP.
2. **`tenant_id` y `branch_id`** generados en servidor (`new_uuid`) una vez por intento
   lógico; no aceptados del cliente.
3. Orden en transacción: reserva idempotencia (pending) → tenant (provisioning) → branch
   → tenant (active) → mark_completed.
4. Exposición futura (HTTP, CLI, jobs) **requiere** guard de rol platform en backend y
   aprobación ADR-0003.

### 3. Idempotencia platform

1. Store en **gym_platform**; operación namespaced (`create_organization`).
2. Clave de documento: **`operation + separador + idempotency_key`** (unicidad en `_id`).
3. Fingerprint SHA-256 canónico sobre payload de negocio (sin IDs de servidor).
4. Estados: `pending` → `completed` (MVP); `failed` reservado.
5. Concurrencia: `DuplicateKeyError` en reserva → lectura independiente y clasificación
   (replay, conflict, in-progress).

**Riesgo aceptado en MVP interno (H2):** la clave es **global** por operación; no hay
aislamiento por actor en el `_id`. Antes de API pública, incluir principal autenticado en
el namespace o validar ownership en application/HTTP.

### 4. Bootstrap técnico de TenantContext

1. Para insertar la primera sucursal sin membership real, se usan UUID **fijos**
   documentados (`CREATE_ORGANIZATION_BOOTSTRAP_*` en `bootstrap_context.py`).
2. Esto **no** constituye autorización criptográfica; solo permite construir
   `TenantContext` válido para `TenantScopedRepository`.
3. Si `created_by_user_id` viene en el comando, se usa como `user_id` del contexto;
   `membership_id` bootstrap hasta existir membership en platform.

### 5. Colecciones lógicas (producción futura)

| Colección (lógica) | Base |
|--------------------|------|
| `tenants` | platform |
| `organization_provisioning_idempotency` | platform |
| `branches` (u otra convención operational) | operational |

Tests de integración **no** usan esos nombres; usan prefijos efímeros (ver
`integration-mongodb.md`).

## Alternativas consideradas

| Alternativa | Motivo de rechazo en H1-D |
|-------------|---------------------------|
| Saga sin transacción | Mayor complejidad y riesgo de estados parciales en MVP. |
| Idempotencia en operational | Mezcla concerns; ADR-0008 concentra metadatos de plataforma en platform. |
| `tenant_id` enviado por cliente | Violación multi-tenant y seguridad. |

## Consecuencias

- Checkpoint backend seguro **sin** superficie HTTP de organization.
- UI-01 puede avanzar asumiendo handler interno; wiring HTTP será fase posterior.
- Integración MongoDB **obligatoria en local** antes de confiar en prod; **no** está en CI.

## Riesgos y mitigaciones

| Severidad | Riesgo | Mitigación |
|-----------|--------|------------|
| **HIGH** | Handler sin guard de invocación | No registrar routers; ADR-0003 + RBAC platform. |
| **HIGH** | Replay idempotente cross-actor | Actor en namespace idempotencia o check HTTP. |
| **MEDIUM** | UoW defaults de concern | Config explícita pre-prod. |
| **MEDIUM** | PyMongo crudo en fallos de insert | Mapper de errores application. |
| **MEDIUM** | Email sin unicidad global | ADR/índice futuro si negocio lo exige. |

## Controles verificables

- `pytest -m "not integration"` (234+ tests unitarios organization/UoW).
- Integración manual: `tests/integration/organization/` (19 tests) con
  `GYM_ERP_RUN_INTEGRATION=1`.
- Sin `list_all` en `PlatformTenantRepository`; tests de guarda H1-C intactos.

## Condiciones de revisión

- Aprobación ADR-0003 y primer endpoint de provisioning.
- Definición de rol platform y membership en alta.
- Decisión sobre actor en claves de idempotencia (H2).
- Configuración de concerns transaccionales en producción (M1).

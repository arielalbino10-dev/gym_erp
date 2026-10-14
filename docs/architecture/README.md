# Arquitectura — Gym ERP

## Vista rápida

```text
[ ERP Web apps/web ] ----HTTPS /api/v1----> [ API apps/api ] ----> [ MongoDB RS ]
[ App móvil apps/mobile ] (futuro) ----/         |
                                                  +-- gym_platform (platform)
                                                  +-- gym_operational (operational)
```

- **Monolito modular** FastAPI; módulos con domain / application / infrastructure / presentation.
- **Multi-tenant:** `tenant_id` obligatorio; permisos solo en backend (ADR-0002).
- **Dos bases lógicas**, un replica set y un `AsyncMongoClient` (ADR-0008).
- **Finanzas operativas** en Release 0.1, no contabilidad formal (ADR-0004).

## Decisiones H1-A.2 (trazabilidad)

| ID | Decisión | Estado | Documento principal |
|----|----------|--------|---------------------|
| D1 | Dos bases platform/operational, un RS, un client | **Accepted** | [ADR-0008](../adr/0008-dos-bases-mongodb-platform-operational.md) |
| D2 | 1 tenant, 1 marca (campos tenant), N sucursales | **Accepted** | [ADR-0009](../adr/0009-modelo-organizacional-mvp.md) |
| D3 | TX multi-base preferida si aplica; idempotencia alternativa | **Accepted** | ADR-0008 §4–5 |
| D4 | `email_normalized` + índices parciales | **Accepted** | [Convenciones](multi-tenant-data-conventions.md) |
| D5 | 404 por id ajeno; listados vacíos/autorizados | **Accepted** | [TenantContext](tenant-context-and-repositories.md) |
| D6 | `database/README.md` solo referencia | **Hecho** | [database/README.md](../../database/README.md) |
| D7 | Roles propuestos, sin ADR-0010 | **Propuesta** | ADR-0009 § roles |
| D8 | Enlace H1-A en README raíz | **Hecho** | [README.md](../../README.md) |

Autenticación (ADR-0003): **Proposed** — ver [pendientes](pending-decisions-auth-0003.md).

## Documentos H1-A (multi-tenant)

| Documento | Contenido |
|-----------|-----------|
| [Convenciones de datos](multi-tenant-data-conventions.md) | UUID, auditoría, índices, `email_normalized` |
| [TenantContext y repositorios](tenant-context-and-repositories.md) | Contrato scoped, anti-IDOR, D5 |
| [Matriz de pruebas de aislamiento](tenant-isolation-test-matrix.md) | ≥2 tenants, T-01–T-15 |
| [Pendientes ADR-0003](pending-decisions-auth-0003.md) | Auth **no** aprobada |

## Otros documentos

- [Estructura del monorepositorio](repository-structure.md)
- [ADR](../adr/README.md)
- [Catálogo de índices (referencia)](../../database/README.md)

## Infraestructura local

MongoDB 8 en `infra/compose/`. Credenciales y keyfile **no** se documentan en el
repositorio; usar `.env` local ignorado por git (repositorio **privado**, software propietario).

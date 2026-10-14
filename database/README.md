# Base de datos — Gym ERP

**Estado (H1-A.2):** solo documentación. No hay scripts de índices, seeds ni migraciones
aplicados en este repositorio todavía.

## Catálogo de índices y convenciones

- Convenciones UUID, auditoría, `email_normalized`, índices compuestos y parciales:
  [docs/architecture/multi-tenant-data-conventions.md](../docs/architecture/multi-tenant-data-conventions.md)
- Partición platform vs operational:
  [ADR-0008](../docs/adr/0008-dos-bases-mongodb-platform-operational.md)
- Aislamiento por tenant:
  [ADR-0002](../docs/adr/0002-aislamiento-multiempresa.md)

## Próximas fases (no autorizadas en H1-A.2)

- Scripts idempotentes de creación de índices (ruta y formato sujetos a aprobación en fase H1-B+).
- Seeds de desarrollo solo en bases `*_test` o entornos locales explícitos.
- Nunca aplicar seeds de prueba a `gym_platform` / `gym_operational` de desarrollo sin
  autorización.

## Infraestructura local

MongoDB 8, replica set `rs0`: [infra/compose/README.md](../infra/compose/README.md).
Credenciales solo en `.env` ignorados por Git.

# Arquitectura — Gym ERP

## Vista rápida

```text
[ ERP Web apps/web ] ----HTTPS /api/v1----> [ API apps/api ] ----> [ MongoDB RS ]
[ App móvil apps/mobile ] (futuro) ----/
```

- **Monolito modular** FastAPI; módulos con domain / application / infrastructure / presentation.
- **Multi-tenant:** `tenant_id` obligatorio; permisos solo en backend (ADR-0002).
- **Finanzas operativas** en Release 0.1, no contabilidad formal (ADR-0004).

## Documentos

- [Estructura del monorepositorio](repository-structure.md)
- [ADR](../adr/README.md)

## Infraestructura local

MongoDB 8 en `infra/compose/`. Credenciales y keyfile **no** se documentan en el
repositorio; usar `.env` local ignorado por git (repositorio **privado**, software propietario).

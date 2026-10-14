# Gym ERP

ERP SaaS B2B para gimnasios tradicionales en México. Monorepositorio con backend
central (`apps/api`) y ERP web administrativo (`apps/web`). Aplicación móvil (Expo)
planificada después de validar el MVP web con gimnasios piloto.

## Stack (resumen)

| Capa | Tecnología |
|------|------------|
| API | Python 3.13, FastAPI, Pydantic, PyMongo Async (`AsyncMongoClient`), uv |
| ERP web | React, Vite, JavaScript (`.jsx`), npm |
| App móvil (futuro) | React Native, Expo, JavaScript (`.jsx`) |
| Base de datos | MongoDB 8.x, replica set |

TypeScript y archivos `.tsx` están prohibidos. Las decisiones detalladas están en
[docs/adr/](docs/adr/README.md).

## Estado del repositorio

- **H0-A:** ADR y documentación base.
- **H0-B:** esqueleto `apps/api` (health live/ready) y `apps/web` (estado de la API).
- **H0-C:** pruebas unitarias, Ruff y workflow GitHub Actions (sin Mongo en CI).
- **H1-A:** arquitectura multi-tenant documentada (ADR-0008, ADR-0009 y guías en [docs/architecture/](docs/architecture/README.md)).
- **Infraestructura local:** MongoDB en [infra/compose/README.md](infra/compose/README.md).

## Estructura

Ver [docs/architecture/repository-structure.md](docs/architecture/repository-structure.md).

## Desarrollo local

1. MongoDB: [infra/compose/README.md](infra/compose/README.md) (`.env` local no versionado).
2. API: [apps/api/README.md](apps/api/README.md) — `uv run uvicorn gym_erp_api.main:app --reload --host 127.0.0.1 --port 8000`
3. Web: [apps/web/README.md](apps/web/README.md) — `npm run dev` (proxy `/api` → API).

Health: [docs/api/health-endpoints.md](docs/api/health-endpoints.md).

## Calidad y CI

Comandos locales y reglas de integración: [docs/development/ci.md](docs/development/ci.md).

## Reglas del proyecto

Cursor aplica las reglas en `.cursor/rules/` (arquitectura, stack, seguridad).

## Licencia

Software propietario. Repositorio privado.

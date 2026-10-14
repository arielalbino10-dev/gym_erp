# Gym ERP API

FastAPI monolith (`gym_erp_api`). H0-B: health checks. H1-B: núcleo multi-tenant
(`TenantContext`, `MongoDatabases`, `TenantScopedRepository`) **sin** endpoints de negocio
ni autenticación (ADR-0003 Proposed).

## Setup

Desde esta carpeta:

```bash
uv sync --all-groups
cp ../../.env.example .env   # editar MONGODB_URI con usuario de aplicación (no root)
```

Variables relevantes: `.env.example` en la raíz (`MONGODB_URI`, `MONGODB_PLATFORM_DB`,
`MONGODB_OPERATIONAL_DB`).

## Run (development)

```bash
uv run uvicorn gym_erp_api.main:app --reload --host 127.0.0.1 --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health/live` | Proceso vivo; no usa MongoDB |
| GET | `/api/v1/health/ready` | 200 si Mongo responde; 503 si no hay URI o falla ping |

No hay rutas públicas con selector de tenant. Un `TenantContext` válido en tests **no**
equivale a identidad autenticada.

## Núcleo multi-tenant (H1-B)

- `shared_kernel/tenant_context.py` — contexto inmutable (UUID validados).
- `infrastructure/mongo/mongo_databases.py` — `gym_platform` / `gym_operational`.
- `infrastructure/mongo/filter_policy.py` — filtros y escrituras seguras.
- `infrastructure/mongo/scoped_repository.py` — acceso operational scoped.

Documentación: [docs/architecture/README.md](../../docs/architecture/README.md).

### Endurecimiento H1-B.1

- Mutaciones (`update_*`, `delete_*`) exigen **filtro de negocio** además del `tenant_id`.
- Agregaciones: lista blanca de etapas y expresiones; sin `allowDiskUse`.
- kwargs PyMongo: lista blanca por método; prohibidos `upsert`, `array_filters`, etc.
- Settings: nombres de BD platform/operational no vacíos y distintos.

## Calidad y pruebas

**Unitarias (como CI, sin MongoDB):**

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not integration" -v
```

Formatear código: `uv run ruff format .`

**Integración MongoDB (manual, autorización explícita):**

```bash
export GYM_ERP_RUN_INTEGRATION=1
export MONGODB_URI_TEST='...'   # BD local *_test; ver docs/development/ci.md
uv run pytest -m integration -v
```

Nunca usar bases `gym_platform` ni `gym_operational` en pruebas.

CI del monorepo: [docs/development/ci.md](../../docs/development/ci.md).

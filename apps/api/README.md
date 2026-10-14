# Gym ERP API

FastAPI monolith (`gym_erp_api`). H0-B: health checks only.

## Setup

Desde esta carpeta:

```bash
uv sync --all-groups
cp ../../.env.example .env   # editar MONGODB_URI con usuario de aplicación (no root)
```

Variables relevantes: ver `.env.example` en la raíz del monorepo.

## Run (development)

```bash
uv run uvicorn gym_erp_api.main:app --reload --host 127.0.0.1 --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health/live` | Proceso vivo; no usa MongoDB |
| GET | `/api/v1/health/ready` | 200 si Mongo responde; 503 si no hay URI o falla ping |

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

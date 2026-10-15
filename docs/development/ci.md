# Integración continua (H0-C)

Workflow: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)

## Qué valida cada job

| Job | Pasos |
|-----|--------|
| **api** | `uv sync --frozen --all-groups`, `ruff check`, `ruff format --check`, `pytest -m "not integration"` |
| **web** | `npm ci`, `npm run lint`, `npm run build` |

No se usa MongoDB, Docker ni secretos del repositorio en CI.

## Comandos locales (equivalentes a CI)

```bash
cd apps/api
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not integration" -v

cd ../web
npm ci
npm run lint
npm run build
```

## Pruebas de integración MongoDB (manual, fuera de CI)

Requieren **autorización explícita** y URI dedicada:

```bash
export GYM_ERP_RUN_INTEGRATION=1
export MONGODB_URI_TEST='mongodb://gym_erp_integration:...@127.0.0.1:27017/gym_operational_test?replicaSet=rs0&authSource=admin'
export MONGODB_PLATFORM_DB=gym_platform_test
export MONGODB_OPERATIONAL_DB=gym_operational_test
cd apps/api
uv run pytest -m integration -v
uv run pytest tests/integration/organization/ -v   # H1-D organization (manual)
```

Reglas de la URI:

- Host: `127.0.0.1` o `localhost` únicamente.
- Allowlist: `gym_platform_test`, `gym_operational_test` (ver
  [integration-mongodb.md](integration-mongodb.md)).
- Usuario URI: `gym_erp_integration` únicamente.
- **Prohibido:** `gym_platform`, `gym_operational`, `gym_erp_app`, `gym_erp_admin`.

No imprimir la URI en logs ni commitear credenciales.

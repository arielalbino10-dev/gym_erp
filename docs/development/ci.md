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
export MONGODB_URI_TEST='mongodb://USER:PASS@127.0.0.1:27017/NOMBRE_test?replicaSet=rs0&authSource=...'
cd apps/api
uv run pytest -m integration -v
```

Reglas de la URI:

- Host: `127.0.0.1` o `localhost` únicamente.
- Base de datos: debe terminar en `_test`.
- **Prohibido:** `gym_platform`, `gym_operational`.

No imprimir la URI en logs ni commitear credenciales.

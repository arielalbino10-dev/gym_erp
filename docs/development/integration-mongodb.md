# MongoDB de integración (H1-C)

Preparación **manual** del entorno local para pruebas de integración y aislamiento
multi-tenant. **No** forma parte de CI. **No** usar bases ni usuarios de desarrollo
(`gym_platform`, `gym_operational`, `gym_erp_app`, `gym_erp_admin`).

## Bases permitidas (allowlist exacta)

| Variable | Valor obligatorio |
|----------|-------------------|
| `MONGODB_PLATFORM_DB` | `gym_platform_test` |
| `MONGODB_OPERATIONAL_DB` | `gym_operational_test` |
| Path en `MONGODB_URI_TEST` | `gym_operational_test` |

Cualquier otro nombre de base rechaza la suite antes de conectar.

## Usuario de integración

- Usuario en URI: **`gym_erp_integration`** (único permitido).
- **Prohibidos:** `gym_erp_admin`, `gym_erp_app` y cualquier otro usuario.
- `authSource=admin` y `replicaSet=rs0` en la query de la URI.
- Host: `127.0.0.1` o `localhost`, puerto **27017**.

Roles esperados (validados vía `connectionStatus` antes de escrituras):

- `readWrite` (o `read`) **solo** sobre `gym_platform_test` y `gym_operational_test`.
- Sin roles globales (`root`, `readWriteAnyDatabase`, etc.) ni acceso a bases productivas.

### Preparación (H1-C.2 — ejecutar con usuario admin, fuera de CI)

1. Crear las bases `gym_platform_test` y `gym_operational_test` en el replica set local.
2. Crear el usuario `gym_erp_integration` en `admin` con contraseña dedicada de prueba.
3. Asignar roles `readWrite` en **ambas** bases de prueba únicamente.
4. Verificar que el usuario **no** tiene privilegios sobre `gym_platform`, `gym_operational`
   ni roles de administración de clúster.

Documentar la contraseña en gestor local (nunca en git). Ejemplo de URI (sin commitear):

```text
mongodb://gym_erp_integration:<PASSWORD>@127.0.0.1:27017/gym_operational_test?replicaSet=rs0&authSource=admin
```

## Interruptor de ejecución

```bash
export GYM_ERP_RUN_INTEGRATION=1
export MONGODB_URI_TEST='...'
export MONGODB_PLATFORM_DB=gym_platform_test
export MONGODB_OPERATIONAL_DB=gym_operational_test
```

Sin `GYM_ERP_RUN_INTEGRATION=1`, las pruebas marcadas `integration` se omiten.

## Harness de datos (H1-C)

- Tenants ficticios: **Titan Gym** y **Olympus Gym** (`tests/support/tenant_fixtures.py`).
- Colección **efímera por sesión** en `gym_operational_test`, prefijo `gym_erp_iso_`.
- Teardown: `drop` **solo** de esa colección tras revalidar nombre y base; **nunca**
  `dropDatabase` ni colecciones ajenas al prefijo.

## Comandos

**H1-C.1 / CI (sin MongoDB):**

```bash
cd apps/api
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not integration" -v
```

**H1-C.3 (autorización explícita, MongoDB real):**

```bash
cd apps/api
uv run pytest -m "integration and tenant_isolation" -v
```

## Implementación en repo

- Validadores: `apps/api/tests/support/integration_environment.py`
- Fixtures: `apps/api/tests/integration/conftest.py`,
  `apps/api/tests/integration/tenant_isolation/conftest.py`
- Matriz: [tenant-isolation-test-matrix.md](../architecture/tenant-isolation-test-matrix.md)

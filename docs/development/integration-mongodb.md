# MongoDB de integración (H1-C, H1-D)

Preparación **manual** del entorno local para pruebas de integración: aislamiento
multi-tenant (H1-C) y módulo **organization** (H1-D). **No** forma parte de CI.
**No** usar bases ni usuarios de desarrollo (`gym_platform`, `gym_operational`,
`gym_erp_app`, `gym_erp_admin`).

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

### Preparación (ejecutar con usuario admin, fuera de CI)

1. Crear las bases `gym_platform_test` y `gym_operational_test` en el replica set local.
2. Crear el usuario `gym_erp_integration` en `admin` con contraseña dedicada de prueba.
3. Asignar roles `readWrite` en **ambas** bases de prueba únicamente.
4. Verificar que el usuario **no** tiene privilegios sobre `gym_platform`, `gym_operational`
   ni roles de administración de clúster.

Documentar la contraseña en gestor local (nunca en git). Ejemplo de URI (sin commitear):

```text
mongodb://gym_erp_integration:<PASSWORD>@127.0.0.1:27017/gym_operational_test?replicaSet=rs0&authSource=admin
```

## Guardias de seguridad (código de tests)

Antes de cualquier escritura, el harness:

1. Valida URI, bases y usuario (`validate_integration_environment`).
2. Ejecuta `connectionStatus` y valida roles (`verify_integration_mongodb_identity`).
3. Crea colecciones **efímeras** solo tras `security_verified=True`.
4. Teardown: `drop` **solo** de la colección registrada si nombre + base + prefijo coinciden.
5. **Prohibido:** `dropDatabase`, colecciones sin prefijo reservado, bases fuera de allowlist.

Implementación: `apps/api/tests/support/integration_environment.py`.

## Interruptor de ejecución

```bash
export GYM_ERP_RUN_INTEGRATION=1
export MONGODB_URI_TEST='...'
export MONGODB_PLATFORM_DB=gym_platform_test
export MONGODB_OPERATIONAL_DB=gym_operational_test
```

Sin `GYM_ERP_RUN_INTEGRATION=1`, las pruebas marcadas `integration` se **omiten** (skip).

Opcional: archivo local ignorado por git, p. ej. `apps/api/.env.integration`, usado con
`uv run --env-file .env.integration` (no versionar).

**No usar `source .env.integration` en zsh/bash** si `MONGODB_URI_TEST` incluye `&` en la
query (`replicaSet=…&authSource=…`): el shell interpreta `&` como operador de fondo. Cargar
con `--env-file` o exportar la URI entre **comillas simples** (`export MONGODB_URI_TEST='…'`).

## Marcadores pytest (`apps/api/pyproject.toml`)

| Marker | Uso |
|--------|-----|
| `integration` | Cualquier prueba contra MongoDB real |
| `tenant_isolation` | Suite H1-C (`tests/integration/tenant_isolation/`) |
| `organization_persistence` | Round-trip repos organization (H1-D.2) |
| `organization_transactions` | MongoUnitOfWork multi-base (H1-D.3.2) |
| `organization_create_organization` | CreateOrganizationHandler (H1-D.3.4) |
| `identity_persistence` | Identity / credenciales / sesiones platform (H2-B.3) |

CI ejecuta únicamente **`pytest -m "not integration"`** (sin MongoDB).

## Harness de datos

### H1-C (tenant isolation)

- Tenants ficticios: **Titan Gym** y **Olympus Gym** (`tests/support/tenant_fixtures.py`).
- Colección efímera en `gym_operational_test`, prefijo **`gym_erp_iso_`**.

### H1-D (organization)

Por sesión de pytest en `tests/integration/organization/conftest.py`:

| Prefijo | Base | Contenido |
|---------|------|-----------|
| `gym_erp_org_plt_` | `gym_platform_test` | Tenants de prueba |
| `gym_erp_org_idm_` | `gym_platform_test` | Idempotencia CreateOrganization |
| `gym_erp_org_op_` | `gym_operational_test` | Sucursales de prueba |

- Colecciones creadas **fuera** de transacciones de prueba (`create_collection`).
- **`reset_organization_ephemeral_collections`** (autouse): `delete_many({})` en las tres
  colecciones antes y después de cada test del módulo organization.
- Teardown de sesión: `drop` de cada colección efímera tras revalidación.

Wiring del handler en tests: `tests/support/create_organization_integration.py`.

### H2-B (identity)

Por sesión en `tests/integration/identity/conftest.py` (solo **`gym_platform_test`**):

| Prefijo | Base | Contenido |
|---------|------|-----------|
| `gym_erp_id_uid_` | `gym_platform_test` | UserIdentity |
| `gym_erp_id_cred_` | `gym_platform_test` | UserCredential (Argon2id) |
| `gym_erp_id_sess_` | `gym_platform_test` | AuthSession (hash de token) |

```bash
cd apps/api
uv run --env-file .env.integration pytest tests/integration/identity -m identity_persistence -v
```

## Comandos

**Unitarias / CI (sin MongoDB):**

```bash
cd apps/api
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not integration" -v
```

**Integración — aislamiento H1-C (manual):**

```bash
cd apps/api
uv run pytest -m "integration and tenant_isolation" -v
```

**Integración — organization completa (manual, H1-D):**

```bash
cd apps/api
# Con variables exportadas o --env-file .env.integration (local, no git)
uv run pytest tests/integration/organization/ -v
```

Subconjuntos:

```bash
uv run pytest -m "integration and organization_persistence" -v
uv run pytest -m "integration and organization_transactions" -v
uv run pytest -m "integration and organization_create_organization" -v
```

**Nota:** La ejecución exitosa de integración es **local del desarrollador**; GitHub Actions
**no** ejecuta estas suites salvo cambio explícito futuro de CI.

## Implementación en repo

- Validadores: `apps/api/tests/support/integration_environment.py`
- Fixtures globales: `apps/api/tests/integration/conftest.py`
- Fixtures H1-C: `apps/api/tests/integration/tenant_isolation/conftest.py`
- Fixtures H1-D: `apps/api/tests/integration/organization/conftest.py`
- Matriz H1-C: [tenant-isolation-test-matrix.md](../architecture/tenant-isolation-test-matrix.md)
- Módulo organization: [organization-module.md](../architecture/organization-module.md)

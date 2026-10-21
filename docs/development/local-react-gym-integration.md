# Integración local React ↔ API gym (H3-C.1)

## Requisitos

- Docker Compose MongoDB (`infra/compose`) con replica set y usuarios documentados en `infra/compose/README.md`.
- Python 3.13+ con `uv` en `apps/api`.
- Node 22+ en `apps/web`.

## Variables (sin secretos en Git)

**API** (`apps/api/.env` o raíz `.env`):

- `APP_ENV=development`
- `MONGODB_URI=…` (usuario app, no root)
- `MONGODB_PLATFORM_DB=gym_platform`
- `MONGODB_OPERATIONAL_DB=gym_operational`
- `CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173`
- `ALLOW_INSECURE_COOKIES=true` (solo local HTTP)

**Web** (`apps/web/.env` opcional):

- Dejar `VITE_API_BASE_URL` sin definir para usar `/api/v1` vía proxy Vite (recomendado).

## Arrancar backend

```bash
cd apps/api
uv run uvicorn gym_erp_api.main:app --reload --host 127.0.0.1 --port 8000
```

## Arrancar frontend

```bash
cd apps/web
npm install
npm run dev
```

Abrir `http://127.0.0.1:5173`.

## Cookies y CSRF

| Recurso | Comportamiento |
|---------|----------------|
| Sesión gym | Cookie HttpOnly `gym_erp_gym_session`, path `/api/v1/gym` |
| CSRF | Cookie legible `gym_erp_gym_csrf` + header `X-CSRF-Token` (mismo valor) |
| Login | `POST /gym/auth/login` — Origin obligatorio; CSRF no exigido sin cookie previa |
| Mutaciones | Origin + header CSRF (token guardado en memoria JS desde respuestas) |
| Renovación CSRF | Tras login, `select-tenant`, logout y mutaciones que emiten token nuevo |
| `GET /session` | Reutiliza el CSRF vigente (cookie + registro server-side); no rota en cada lectura |

El cliente React **no** guarda tokens de sesión en `localStorage`. El CSRF vive en memoria de la pestaña y se refresca desde el header de respuesta.

## Bootstrap de datos de desarrollo (opt-in)

Requisitos de configuración en `apps/api/.env` (manual):

- `APP_ENV=development`
- `MONGODB_URI=mongodb://…@127.0.0.1:27017/?replicaSet=rs0` (localhost, replica set)
- `MONGODB_PLATFORM_DB=gym_platform`
- `MONGODB_OPERATIONAL_DB=gym_operational`
- **No** usar bases `*_test` en este flujo manual.

Primera ejecución (crea usuario, tenant estable por email, membresía owner y sucursal inicial):

```bash
cd apps/api
export GYM_ERP_BOOTSTRAP_GYM=1
export GYM_ERP_DEV_BOOTSTRAP_PASSWORD='su-contraseña-local-min-12-caracteres'
export GYM_ERP_DEV_BOOTSTRAP_EMAIL='dev.gym.owner@local.test'
uv run python scripts/bootstrap_local_gym_dev.py
```

Antes de reintentar tras un fallo, inspección **solo lectura**:

```bash
export GYM_ERP_BOOTSTRAP_GYM=1
export GYM_ERP_DEV_BOOTSTRAP_INSPECT=1
export GYM_ERP_DEV_BOOTSTRAP_EMAIL='dev.gym.owner@local.test'
uv run --env-file .env python scripts/bootstrap_local_gym_dev.py
```

Ejecuciones repetidas con el **mismo email** reutilizan el tenant UUID v4 ya vinculado por **membresía activa** `gym_owner` al gimnasio bootstrap (`Dev Gym Local` + legal name de desarrollo). **No** crean gimnasios duplicados.

Si el usuario `@local.test` **ya tiene credencial**, el script **no** cambia la contraseña: muestra un aviso en stderr y continúa asegurando tenant/membresía/sucursal. Use la contraseña que configuró antes o elimine la credencial manualmente solo en desarrollo.

Opcional: `GYM_ERP_DEV_TENANT_ID=<uuid-v4>` solo si ya tiene membresía en ese tenant o el tenant aún no existe; debe ser UUID **v4**.

**No** commitear contraseñas. El script no imprime hashes ni URI con credenciales.

## Flujo de prueba manual

1. Bootstrap (o datos equivalentes ya existentes en dev).
2. `npm run dev` + API en :8000.
3. `/login` → email/contraseña del bootstrap.
4. `/seleccionar-gimnasio` → elegir tenant.
5. `/sucursales` → listado MongoDB operational.
6. Crear sucursal (owner/admin) → confirmar en lista.
7. Refrescar navegador → sesión + listado persisten.

## Errores frecuentes

| Código | Causa habitual |
|--------|----------------|
| 401 | Sesión ausente/expirada; volver a login |
| 403 | CSRF (`code: csrf_invalid`), permiso, tenant no seleccionado — no cierra sesión salvo flujo explícito |
| 503 | API sin MongoDB o infra identity/access no compuesta |

## CORS

Con proxy Vite, el navegador ve origen `127.0.0.1:5173` y API relativa `/api/v1` — mismo sitio para cookies.

Si apunta `VITE_API_BASE_URL` al puerto 8000, configure `CORS_ORIGINS` y use credenciales; el API expone `X-CSRF-Token` en CORS.

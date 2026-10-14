# Health endpoints (H0-B)

Prefijo de API: **`/api/v1`**.

## GET /api/v1/health/live

- **Propósito:** Liveness del proceso API.
- **MongoDB:** no consulta la base de datos.
- **200:** `{ "status": "ok" }`
- **Uso:** balanceadores y comprobaciones locales sin credenciales Mongo.

## GET /api/v1/health/ready

- **Propósito:** Readiness; el servicio puede atender tráfico que depende de MongoDB.
- **200:** `{ "status": "ready" }` — ping administrativo a MongoDB exitoso.
- **503:** `{ "status": "not_ready" }` — sin `MONGODB_URI`, cliente no inicializado o ping fallido.
- **Seguridad:** la respuesta no incluye URI, hosts internos, versiones de servidor ni stack traces.

## Configuración

| Variable | Descripción |
|----------|-------------|
| `MONGODB_URI` | URI completa con usuario de **aplicación** (no root). Opcional en H0-B hasta crear usuario. |
| `MONGODB_PING_TIMEOUT_MS` | Timeout de selección de servidor (default 2000). |

Autenticación JWT u otros secretos: ver ADR-0003 (**Proposed**); no forman parte de H0-B.

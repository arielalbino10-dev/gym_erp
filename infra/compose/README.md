# MongoDB local (Docker Compose)

Entorno de **desarrollo** para Gym ERP. No usar como producción.

## Requisitos

- Docker Desktop (Mac Apple Silicon u otro host compatible).
- Archivo `.env` en esta carpeta ( **no versionado** ) con las variables que exige
  `compose.yaml`:
  - `MONGO_ROOT_USERNAME`
  - `MONGO_ROOT_PASSWORD`

Las **contraseñas y URIs reales** viven solo en archivos `.env` locales (por ejemplo
`infra/compose/.env` y `apps/api/.env`). No documentar ni commitear valores reales.
El `.gitignore` del monorepo ignora esos `.env` y `infra/compose/mongodb/mongo.keyfile`.
Use `.env.example` en la raíz del monorepo como plantilla con valores ficticios.

## Servicio

| Elemento | Valor |
|----------|--------|
| Imagen | `mongo:8.0` |
| Contenedor | `gym_erp_mongodb` |
| Puerto host | `127.0.0.1:27017` |
| Replica set | `rs0` (requerido para transacciones) |
| Autenticación | `--auth` + `--keyFile` |

## Arranque (referencia)

Desde esta carpeta, con `.env` configurado:

```bash
docker compose up -d
```

**No ejecutar** `docker compose down -v` salvo autorización explícita (destruye datos).

## Replica set

Tras el primer arranque, el replica set debe quedar inicializado (`PRIMARY`).
Si el contenedor ya fue configurado previamente, no repetir `rs.initiate` ni
`rs.reconfig` sin autorización.

Procedimiento típico (solo cuando el entorno es nuevo y está autorizado):

1. Entrar al contenedor con herramientas de administración (mongosh).
2. `rs.initiate({ _id: "rs0", members: [{ _id: 0, host: "localhost:27017" }] })`.
3. Verificar `rs.status()` → estado `PRIMARY`.

Los pasos exactos pueden variar según red Docker; documentar lo que aplique en tu
máquina sin publicar credenciales.

## Usuarios MongoDB (administrador vs aplicación)

En el entorno local confirmado conviven dos cuentas con roles distintos:

| Rol | Usuario (ejemplo) | Uso |
|-----|-------------------|-----|
| **Administrador** | `gym_erp_admin` | Creación de usuarios, índices y tareas operativas en MongoDB. En Compose, las variables `MONGO_ROOT_USERNAME` / `MONGO_ROOT_PASSWORD` de `infra/compose/.env` alimentan el usuario root de inicialización del contenedor; en desarrollo ese usuario administrativo corresponde a `gym_erp_admin`. **No** usar esta cuenta en FastAPI ni en clientes. |
| **Aplicación** | `gym_erp_app` | Conexión de la API. Usuario ya creado y autenticado; permisos `readWrite` sobre `gym_platform` y `gym_operational`. |

La API (`apps/api`) debe conectarse **únicamente** con `gym_erp_app` mediante
`MONGODB_URI` en `apps/api/.env` (formato ilustrativo en `.env.example` de la raíz:
usuario `gym_erp_app`, base `gym_operational`, `replicaSet=rs0`, `authSource=admin`).

Comportamiento de health:

- `GET /api/v1/health/live` no depende de MongoDB.
- `GET /api/v1/health/ready` responde **`ready`** cuando `MONGODB_URI` es válida y el
  ping a MongoDB (replica set `rs0`) tiene éxito; en caso contrario responde **503**.

No incluir contraseñas ni URIs con credenciales en documentación versionada.

## Bases de datos

- **`gym_platform`**: datos de plataforma / multi-tenant (según evolución del producto).
- **`gym_operational`**: datos operativos del gimnasio en desarrollo; es la base
  referenciada en `.env.example` para la API.
- **Pruebas de integración**: bases dedicadas con sufijo `_test` (nunca reutilizar
  `gym_platform` ni `gym_operational` como destino de pruebas automatizadas).

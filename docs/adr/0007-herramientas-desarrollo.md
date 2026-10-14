# ADR-0007: Herramientas de desarrollo (uv, npm, Docker)

- **Estado:** Accepted
- **Fecha:** 2026-10-13 (documentación H0-A)
- **Decisores:** Propietario del producto

## Contexto

Equipo de un desarrollador apoyado por Cursor AI; bajo costo operativo; **prohibido
TypeScript** en el monorepo. MongoDB local ya opera en `infra/compose/` con replica set
y autenticación (configuración existente, no versionada en detalle).

## Decisión

1. **Python:** gestión con **uv** (entorno, dependencias, lockfile `uv.lock` en fase H0-B).
   Versión de referencia del entorno: **Python 3.13.x**.
2. **JavaScript (ERP web):** **npm** con `package-lock.json`; **npm ci** en CI (fase posterior).
   **Node.js 22 LTS** como referencia.
3. **Prohibido TypeScript** y archivos `.tsx` en el monorepo.
4. **Docker** en H0/H1: principalmente **servicios de desarrollo** (MongoDB 8.x en
   `infra/compose/`). API y web se ejecutan en el host con uv/npm salvo que un ADR
   futuro de despliegue decida contenedorizar producción.
5. **No se asume** que Docker sea exclusivo de desarrollo para siempre; la estrategia
   de hosting producción queda **pendiente** (ADR de despliegue futuro).
6. **Calidad (fases posteriores):** Ruff + pytest en API; ESLint en web. Solo dependencias
   esenciales, compatibles y mantenidas; cada dependencia nueva requiere autorización.
7. **Driver MongoDB:** PyMongo con **`AsyncMongoClient`** (API async nativa); no Motor.

## Alternativas consideradas

- **Poetry/pip-tools:** descartados frente a uv por velocidad e integración.
- **pnpm/yarn:** innecesarios con un paquete JS inicial.
- **API/web en Docker en dev:** más lento en macOS; descartado para H0.

## Consecuencias

- Reproducibilidad vía lockfiles cuando existan `apps/api` y `apps/web`.
- Dependencia de Docker Desktop en Mac para Mongo local (decisión operativa del equipo).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| uv o Node cambian comportamiento | Fijar versiones en CI y documentación |
| Sin tipado TS, errores de contrato | OpenAPI, tests, revisión |
| Compose local distinto a CI | Documentar patrón RS en CI en H0-C |

## Controles verificables

- `.env.example` en raíz sin secretos reales.
- `.gitignore` ignora `.env`, keyfiles y credenciales Mongo.
- H0-A no añade `pyproject.toml` ni `package.json` (reservado H0-B).

## Condiciones de revisión

- ADR de despliegue producción (contenedores, Atlas, etc.).
- Inicio de `apps/mobile` (evaluar npm workspaces).

# ADR-0001: Monorepositorio y monolito modular FastAPI

- **Estado:** Accepted
- **Fecha:** 2026-10-13 (documentación H0-A)
- **Decisores:** Propietario del producto

## Contexto

Gym ERP es un SaaS multiempresa para gimnasios en México. El equipo inicial es un
desarrollador apoyado por herramientas de IA. Se requiere un backend único para el ERP
web (Release 0.1) y una futura app móvil, con mantenibilidad y bajo costo operativo,
sin microservicios prematuros.

## Decisión

1. **Monorepositorio** con rutas principales:
   - `apps/api` — backend FastAPI (Python), API REST en `/api/v1`.
   - `apps/web` — ERP administrativo React + Vite (`.jsx`).
   - `apps/mobile` — React Native + Expo (`.jsx`); reservado; no implementar hasta priorización aprobada.
   - `docs/`, `infra/`, y en fases posteriores `packages/`, `database/`.
2. **Monolito modular** con Clean Architecture pragmática por módulo de negocio:
   `domain`, `application`, `infrastructure`, `presentation`.
3. Configuración y servicios transversales en un núcleo mínimo (`shared_kernel` / `core`),
   sin concentrar reglas de negocio.
4. Los clientes (web/móvil) **nunca** acceden a MongoDB.

## Alternativas consideradas

- **Microservicios:** descartados por costo operativo y tamaño del equipo.
- **Multirepo:** descartado; dificulta cambios coordinados de contrato API y CI.
- **Monolito sin módulos:** descartado; reduce claridad al crecer.

## Consecuencias

- Un despliegue de API, un contrato OpenAPI, cambios atómicos API + web en el mismo repo.
- Disciplina necesaria para no romper límites entre módulos (imports, acceso a datos).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Dependencias circulares entre módulos | Puertos en dominio, eventos internos, revisión de código |
| CI más lento al crecer | Jobs separados por `apps/api` y `apps/web` |
| Acoplamiento del frontend al backend | Contrato `/api/v1` versionado; reglas de negocio solo en API |

## Controles verificables

- Estructura de carpetas documentada en `docs/architecture/repository-structure.md`.
- Nuevos módulos siguen las cuatro capas; acceso a MongoDB solo en `infrastructure`.
- Cambios de límites entre módulos requieren nuevo ADR aprobado.

## Condiciones de revisión

- Necesidad demostrada de despliegue o escalado independiente de un módulo.
- Más de un equipo con conflictos frecuentes en el monorepo.
- Tiempo de CI que impida iterar (umbral a definir con el propietario).

# ADR-0008: Dos bases MongoDB (platform y operational)

- **Estado:** Accepted
- **Fecha:** 2026-10-14 (documentación H1-A.2)
- **Decisores:** Propietario del producto (decisión D1)

## Contexto

Gym ERP es SaaS multiempresa (ADR-0002). La infraestructura local ya opera MongoDB 8
como replica set `rs0` con las bases lógicas `gym_platform` y `gym_operational`
(documentadas en `infra/compose/README.md`). Hasta H0-C la API usa un único
`AsyncMongoClient` y una URI con la base operativa en el path.

Se requiere formalizar **qué datos viven en cada base** sin cambiar las invariantes de
aislamiento por `tenant_id` ni introducir microservicios.

## Decisión

1. **Un solo cluster MongoDB** (replica set) y **un `AsyncMongoClient`** por proceso API
   (ADR-0007, PyMongo async). Acceso a bases por nombre lógico, p. ej. `client[platform_db_name]` y
   `client[operational_db_name]`. Los nombres de base serán **configurables** en fases
   posteriores (sin fijar valores reales en este ADR).
2. **`gym_platform`** (nombre de referencia): identidad de plataforma, tenants, membresías
   usuario–tenant, suscripciones SaaS, sesiones de autenticación (cuando ADR-0003 esté
   aprobado e implementado), auditoría de plataforma. **No** contiene datos operativos de
   socios, cobros ni asistencia.
3. **`gym_operational`** (nombre de referencia): datos del negocio del gimnasio scoped por
   `tenant_id`: sucursales, socios, planes, membresías comerciales, pagos operativos,
   asistencia, auditoría operativa. Colecciones **compartidas entre tenants** con
   `tenant_id` obligatorio (ADR-0002).
4. **Transacciones multi-base (mismo replica set):** cuando varias escrituras **cortas**
   en platform y operational deban ser **atómicas**, se **prefiere** una transacción
   MongoDB que abarque ambas bases en el **mismo** replica set. **No** es obligatorio
   usar transacciones para todo el onboarding ni para flujos largos.
5. **Alternativa idempotente:** cuando la transacción no sea adecuada (operación larga,
   reintentos externos, límites de transacción), documentar en el caso de uso un orden
   idempotente con claves de idempotencia y compensación manual o jobs de reconciliación
   (fase posterior).
6. Las reglas de **repositorios scoped**, `TenantContext` y pruebas de aislamiento
   (ADR-0002, docs de arquitectura H1-A) aplican a la base operational; la base platform
   usa repositorios dedicados sin sustituir el filtro `tenant_id` en operational.

## Alcance no cubierto (pendiente de otros ADR)

- Autenticación y formato de sesión (ADR-0003, **Proposed**).
- Catálogo definitivo de colecciones e índices físicos (documentación en
  `database/README.md` y `docs/architecture/multi-tenant-data-conventions.md`; aplicación
  en fase posterior autorizada).
- Aprovisionamiento automático de tenants, billing y despliegue producción.

## Alternativas consideradas

- **Base de datos por tenant (ADR-0002):** reservada para requisitos enterprise; no MVP.
- **Una sola base para todo:** mezcla platform y operational; descartada por claridad de
  límites y permisos MongoDB futuros.
- **Saga obligatoria para toda escritura cross-base:** descartada; transacción RS preferida
  cuando aplica; idempotencia en otros casos (D3).
- **Dos clientes MongoDB:** innecesario; un client, múltiples handles de base de datos.

## Consecuencias

- La capa `infrastructure` debe distinguir explícitamente repositorios platform vs
  operational (implementación H1-B+).
- Onboarding puede requerir coordinación cross-base; diseño debe elegir transacción o
  idempotencia por caso.
- Backups y restores deben considerar **ambas** bases del mismo cluster.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Olvidar filtro `tenant_id` en operational | Repositorios scoped; tests `tenant_isolation`; índices no sustituyen filtro |
| Transacciones largas o fallidas | Solo escrituras cortas; timeout; fallback idempotente documentado |
| Inconsistencia platform/operational sin TX | Idempotency keys; reconciliación; preferir TX cuando sea crítico |
| Confusión de base en código | Nombres configurables; factories por base; revisión de código |

## Controles verificables

- Documentación de convenciones e índices en `docs/architecture/`.
- Ningún router accede a colecciones sin capa repository (ADR-0002).
- Pruebas de aislamiento en operational con ≥2 tenants antes de piloto (ADR-0002).

## Condiciones de revisión

- Requisito de aislamiento físico por tenant (volver a ADR-0002).
- MongoDB Atlas / sharding con límites distintos a transacciones multi-base locales.
- Separación de clusters por región o compliance.

## Referencias

- [ADR-0002: Aislamiento multiempresa](0002-aislamiento-multiempresa.md)
- [ADR-0009: Modelo organizacional MVP](0009-modelo-organizacional-mvp.md)
- [Convenciones de datos](../architecture/multi-tenant-data-conventions.md)

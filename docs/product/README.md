# Producto — Gym ERP

## Resumen

- **Cliente pagador:** gimnasios (B2B), México, gimnasios tradicionales.
- **Release 0.1 (objetivo):** ERP web — auth, socios, planes, membresías, cobros
  manuales, vencimientos, check-in manual, auditoría básica, aislamiento multi-tenant probado.
- **App móvil:** después de pilotos web (ADR-0005).
- **Finanzas:** operativas; sin CFDI ni contabilidad formal en 0.1 (ADR-0004).

## Fases de implementación (referencia)

| Fase | Alcance |
|------|---------|
| **H0-A** | ADR y documentación (actual) |
| **H0-B** | Esqueleto `apps/api` + `apps/web`, health, sin negocio |
| **H0-C** | CI, pruebas de integración Mongo, harness 2 tenants |
| **Release 0.1** | Módulos E0.x según plan maestro v3 |

Los entregables E0.x y criterios de aceptación detallados permanecen en el plan maestro;
no se duplican aquí salvo cambios aprobados por ADR.

## Hipótesis comerciales (no confirmadas)

Precio SaaS por tramos, CAC, disposición a pagar, coste de hosting y momento de inversión
en app móvil permanecen **pendientes de validación** con pilotos.

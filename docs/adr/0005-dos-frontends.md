# ADR-0005: Dos frontends oficiales (ERP web y app móvil)

- **Estado:** Accepted
- **Fecha:** 2026-10-13 (documentación H0-A)
- **Decisores:** Propietario del producto

## Contexto

El primer producto entregable es el **ERP web** para dueño y recepción (formularios,
tablas, cobranza, check-in manual). Una **app móvil** (Expo) para socios y/o personal
en sitio se priorizará **después** de validar el MVP web con gimnasios piloto. El
backend debe servir ambos con un contrato común. TypeScript está prohibido.

## Decisión

1. **`apps/web`:** React + Vite, JavaScript `.jsx`, interfaz administrativa responsive.
   **Único frontend implementado en Release 0.1.**
2. **`apps/mobile`:** React Native + Expo, JavaScript `.jsx`. **Aprobado como parte de
   la arquitectura; no se implementa en H0 ni en Release 0.1** hasta priorización
   explícita del propietario tras pilotos.
3. Ambos consumen **`/api/v1`** en `apps/api`. Reglas de negocio, permisos, tenant y
   montos solo en el backend.
4. UI **no compartida** entre web y móvil; código JS compartido solo si aporta valor
   (p. ej. cliente HTTP) en `packages/`, con ADR adicional si crece el alcance.
5. Aceptar **Expo como tecnología móvil futura** no implica iniciar desarrollo móvil
   en paralelo al ERP web.

## Alternativas consideradas

- **Expo Web como único cliente:** descartado para ERP administrativo denso.
- **Web y móvil en paralelo desde 0.1:** descartado por priorización del propietario.
- **TypeScript:** prohibido por reglas del proyecto.

## Consecuencias

- Mejor UX web en el piloto; dos codebases frontend a futuro.
- API debe diseñarse agnóstica del cliente (sin endpoints “solo web” salvo transporte auth).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| API acoplada a web | OpenAPI; revisión de contrato; tests de contrato |
| Reglas de negocio en `.jsx` | Lint/revisión; backend revalida todo |
| Presión por app móvil antes de piloto | Criterios de activación documentados en producto |

## Controles verificables

- Release 0.1 no contiene `apps/mobile` funcional ni pipelines móviles.
- Cambios breaking en `/api/v1` documentados y versionados cuando aplique.

## Condiciones de revisión

- Cierre de pilotos web con demanda documentada de app móvil.
- Duplicación insostenible de lógica de presentación entre clientes.

## Criterios de activación móvil (referencia)

- Release 0.1 web en uso por al menos un gym piloto (periodo acordado).
- Alcance móvil aprobado en ADR nuevo.
- Capacidad del equipo confirmada.

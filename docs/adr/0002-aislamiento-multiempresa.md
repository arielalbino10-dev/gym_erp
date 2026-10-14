# ADR-0002: Aislamiento multiempresa en MongoDB

- **Estado:** Accepted
- **Fecha:** 2026-10-13 (documentación H0-A)
- **Decisores:** Propietario del producto

## Contexto

El producto es SaaS: varios gimnasios (tenants) comparten la plataforma. Cada tenant
puede tener varias sucursales. Debe impedirse el acceso cruzado entre gimnasios y
validarse el alcance por sucursal en el backend. Las reglas de seguridad exigen probar
el aislamiento entre empresas.

Este ADR define **invariantes de datos y acceso**, independientes del mecanismo exacto
de autenticación (ver ADR-0003, Proposed).

## Decisión

1. **Base operativa MongoDB compartida** entre tenants (colecciones compartidas).
2. Todo documento con datos de un tenant incluye **`tenant_id` obligatorio**; datos de
   sucursal incluyen **`branch_id`** cuando aplique.
3. El **`tenant_id` activo se resuelve exclusivamente en el servidor** a partir del
   contexto autenticado (sesión/token validado). **No** se acepta `tenant_id` ni
   `branch_id` del cliente como fuente de autorización (body, query, headers arbitrarios).
4. Lecturas y escrituras pasan por **repositorios con alcance de tenant** en
   `infrastructure`; prohibido acceso directo a colecciones fuera de esa capa.
5. **Índices** compuestos con prefijo `tenant_id`; unicidad de negocio siempre acotada
   por tenant.
6. Desde **Release 0.1**, pruebas automatizadas con **al menos dos tenants** que
   demuestren que un tenant no lee ni modifica datos de otro; alcance por sucursal
   para roles restringidos (p. ej. recepción).
7. MongoDB debe ejecutarse como **replica set** en todos los entornos donde se usen
   **transacciones** (desarrollo incluido). La inicialización del replica set es
   responsabilidad de la infraestructura local (`infra/compose/`); no forma parte de
   este ADR operativo.

## Alternativas consideradas

- **Base de datos por tenant:** mayor aislamiento; más costo y operación; posible evolución enterprise.
- **Colección por tenant:** proliferación de colecciones e índices; descartado.
- **Confianza en filtros enviados por el frontend:** descartado (inseguro).

## Consecuencias

- Onboarding de tenants sin aprovisionar BD nueva.
- Responsabilidad alta en la capa de repositorio y en pruebas de aislamiento.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Omisión de filtro `tenant_id` | Repositorio único con scope; tests en CI; revisión de código |
| Agregaciones/`$lookup` sin filtro inicial | Política de código + tests |
| Respuesta que revela existencia de recursos ajenos | Política 404 uniforme (detalle en implementación; alinear con ADR-0003) |

## Controles verificables

- Suite `tenant_isolation` en CI verde antes de release piloto.
- Catálogo de índices documentado (fase `database/`) con prefijo `tenant_id`.
- Ningún router accede a `AsyncMongoClient` sin pasar por repositorio scoped.

## Condiciones de revisión

- Requisito contractual de aislamiento físico por tenant.
- Degradación de rendimiento por vecino ruidoso no mitigable.
- Residencia de datos por región.

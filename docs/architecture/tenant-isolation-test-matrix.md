# Matriz de pruebas de aislamiento multi-tenant

Documento de referencia H1-A.2. Obligatoriedad de cobertura alineada con **ADR-0002**
(≥2 tenants antes de release piloto). **No** ejecuta pruebas ni crea datos en MongoDB
en H1-A.2.

## Entorno de prueba

- Bases dedicadas con sufijo **`_test`** (p. ej. `gym_operational_integration_test`), nunca
  `gym_platform` ni `gym_operational` de desarrollo (guardia en `apps/api/tests/`).
- Integración MongoDB solo con `GYM_ERP_RUN_INTEGRATION=1` y URI validada (ver
  `docs/development/ci.md`).
- Datos **ficticios**: `tenant_a`, `tenant_b` con UUIDs fijos en fixtures; usuarios y
  memberships coherentes en platform de prueba.
- CI unitaria: **`pytest -m "not integration"`**; suite `tenant_isolation` con mocks de
  repositorio + integración autorizada manual/CI futuro con Mongo.

## Matriz

| ID | Escenario | Precondición | Acción | Resultado esperado |
|----|-----------|--------------|--------|-------------------|
| T-01 | Lectura cruzada por id | Mismo tipo de doc en A y B | Contexto A, get id de B | **404** (D5); cero datos de B |
| T-02 | Listado | Docs en A y B | Contexto A, list | Solo A; **nunca** filas de B |
| T-03 | Update cruzado | Doc en B | Contexto A, update id B | **404**; B sin cambios |
| T-04 | Delete cruzado | Doc en B | Contexto A, delete id B | **404**; B intacto |
| T-05 | Unicidad por tenant | Mismo `email_normalized` | Crear en A y en B | Ambos OK (índice `{tenant_id, email_normalized}`) |
| T-06 | Duplicado en tenant | Mismo email dos veces en A | Segundo insert | Error duplicate key |
| T-07 | Sin membresía | User sin membership en A | Request autenticado (futuro) | **403** |
| T-08 | Agregación | Pipeline sin `$match` tenant | Repo scoped | 0 docs ajenos o test falla en revisión |
| T-09 | `update_many` | Docs A y B | Scoped A | Solo docs A modificados |
| T-10 | Header/query tenant falso | Sesión/contexto A | Cliente envía `tenant_id=B` | Ignorado; sigue A |
| T-11 | Branch scope (propuesta rol recepción) | Membership limitada a branch X | List/get branch Y | Listado **vacío**; GET por id de Y → **404** (D5) |
| T-12 | Filtro malicioso en repo | Unit test | Filtro `{tenant_id: B}` desde app | Repositorio **rechaza** (excepción infra) |
| T-13 | Operador prohibido | Unit test | `$or` con rama sin tenant del contexto | Repositorio **rechaza** (no “filtro forzado” silencioso) |
| T-14 | Sin tenant en contexto | Ruta exige tenant | Request | **401/403** (con auth); no 200 con datos |
| T-15 | Índice sin filtro | Test documental | Query sin tenant en código | Fallo de revisión/linters futuros; test negativo |

## Tipos de prueba

| Tipo | Qué valida |
|------|------------|
| **Unit** | Fusión de filtros, rechazo de sobrescritura, sanitización de operadores |
| **Integration** | T-01–T-11 contra Mongo `*_test` |
| **Contract/API** | T-01, T-02, T-03, T-10, T-14 cuando existan endpoints (post ADR-0003) |

## Ubicación prevista en repo

```text
apps/api/tests/tenant_isolation/
```

## Referencias

- [ADR-0002](../adr/0002-aislamiento-multiempresa.md)
- [TenantContext y repositorios](tenant-context-and-repositories.md)
- [Convenciones de datos](multi-tenant-data-conventions.md)

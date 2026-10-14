# TenantContext y repositorios scoped (contrato conceptual)

Documento de referencia H1-A.2. Describe comportamiento **obligatorio** para
implementación H1-B+; **no** hay código productivo ni endpoints de negocio en H1-A.2.

## Estado de decisiones

| Tema | Estado |
|------|--------|
| Resolución de `tenant_id` solo en servidor | **Aprobado** (ADR-0002) |
| 404 recurso ajeno; listados vacíos/autorizados | **Aprobado** (D5) |
| Repositorios rechazan sobrescritura de `tenant_id` | **Aprobado** (H1-A.2) |
| Origen del contexto vía auth/sesión | **Pendiente** (ADR-0003 Proposed) |

## TenantContext

Objeto **inmutable** por request (o por unidad de trabajo acotada) construido **solo** en
capa bootstrap/application **después** de validar identidad y membresía cuando exista
autenticación (ADR-0003).

Campos conceptuales mínimos:

| Campo | Descripción |
|-------|-------------|
| `tenant_id` | Tenant activo confiable |
| `user_id` | Usuario de plataforma autenticado |
| `membership_id` | Membresía activa usuario–tenant (platform) |
| `allowed_branch_ids` | `None` = todas las permitidas por rol; lista = restricción. Depende de roles **propuestos** en ADR-0009 (no aprobados como RBAC definitivo). |

Extensiones futuras (permisos materializados, subscription gate) no forman parte de
H1-A.2.

### Origen permitido del contexto

1. **Producción / endpoints públicos de negocio:** únicamente cadena **autenticación →
   sesión/servidor → membresía activa → tenant activo en sesión** (ADR-0003 cuando esté
   Accepted e implementado). El cliente **no** autoriza enviando `tenant_id` en query,
   body o headers arbitrarios (ADR-0002).
2. **Tests unitarios de repositorio:** inyección explícita de `TenantContext` en el
   constructor o factory del repositorio — **permitido**.
3. **Prohibido:** inyectar contexto simulado o “stub” en dependencies de FastAPI que
   expongan **endpoints HTTP de negocio** como si estuvieran autenticados. Hasta tener
   ADR-0003 implementado, no existen esos endpoints públicos con tenant.

## Repositorios scoped (operational)

### Responsabilidades

- Reciben handle de colección + `TenantContext` fijado en construcción.
- **Fusionan** el filtro de tenant confiable en **todas** las operaciones de lectura,
  actualización, borrado y agregación iniciadas por el repositorio.
- **Ningún** método público del repositorio acepta un filtro “libre” sin sanitizar.

### Reglas anti–sobrescritura de `tenant_id`

El repositorio debe **rechazar** (error de programación / excepción de infraestructura,
no respuesta HTTP directa) cuando el caller intente:

- Incluir `tenant_id` distinto al del contexto en filtros, proyecciones de update o
  pipelines de agregación pasados desde capas superiores.
- Usar operadores que eludan el scope: p. ej. `$where`, `$expr` no acotados, `$or` con
  rama sin `tenant_id` del contexto, `$nor` que excluya el tenant confiable.
- **`$set` / replace** que modifiquen `tenant_id` en documentos existentes.

Política de construcción de filtro seguro:

```text
safe_filter = { "tenant_id": ctx.tenant_id, **sanitized_user_filter }
```

donde `sanitized_user_filter` **no** contiene claves reservadas (`tenant_id`, `$where`, …)
ni operadores prohibidos por lista blanca.

### Respuestas HTTP (capa presentation, D5)

| Operación | Cross-tenant / inexistente en tenant |
|-----------|--------------------------------------|
| GET por id | **404 Not Found** (no revelar existencia en otro tenant) |
| GET listado | **200** con conjunto vacío o solo registros autorizados del tenant |
| PATCH/DELETE | Solo documentos del tenant confiable; si id existe en otro tenant → **404** |
| Sin contexto tenant válido en ruta que lo exige | **401/403** según auth (detalle con ADR-0003) |

Las mutaciones **nunca** aplican cambios fuera del `tenant_id` confiable aunque el id
sea adivinado.

## Repositorios platform

- Acceden a `gym_platform`; no sustituyen el aislamiento operational.
- Consultas por `tenant_id` cuando la colección es per-tenant (p. ej. memberships).
- Sesiones y usuarios: reglas propias; sin mezclar datos de socios operativos.

## Transacciones (recordatorio ADR-0008)

Preferir transacción multi-base en RS para pocas escrituras atómicas platform+operational;
repositorios participan con el mismo `tenant_id` acordado en el caso de uso.

## Referencias

- [ADR-0002](../adr/0002-aislamiento-multiempresa.md)
- [ADR-0008](../adr/0008-dos-bases-mongodb-platform-operational.md)
- [Pendientes ADR-0003](pending-decisions-auth-0003.md)
- [Matriz de pruebas](tenant-isolation-test-matrix.md)

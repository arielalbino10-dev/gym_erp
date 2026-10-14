# Convenciones de datos multi-tenant

Documento de referencia (H1-A.2). **No** aplica índices ni colecciones en MongoDB hasta
fase autorizada. Complementa ADR-0002 (Accepted), ADR-0008 y ADR-0009 (Accepted).

## Estado de decisiones

| Tema | Estado |
|------|--------|
| UUID, auditoría, prefijo `tenant_id` en índices | **Aprobado** (H1-A.2, alineado ADR-0002) |
| `email_normalized` e índices parciales | **Aprobado** (D4) |
| Respuesta HTTP cross-tenant (404 vs lista vacía) | **Aprobado** (D5); detalle en [tenant-context-and-repositories.md](tenant-context-and-repositories.md) |

## Identificadores (UUID)

- Usar **UUID v4** en string canónico (minúsculas, con guiones) para identificadores de
  dominio: `tenant_id`, `branch_id`, `user_id`, `member_id`, etc.
- Campo de negocio explícito (`tenant_id`, …) además de `_id` de MongoDB cuando ambos
  existan: `_id` puede igualar el UUID de dominio en entidades raíz (decisión de
  implementación H1-B); lo importante es **inmutabilidad** y no reutilizar IDs.
- No usar ObjectId autoincremental como identificador expuesto en API pública.

## Campos de auditoría

Recomendados en documentos mutables:

| Campo | Uso |
|-------|-----|
| `created_at` | UTC, ISO-8601 |
| `updated_at` | UTC, actualizado en cada mutación |
| `created_by_user_id` | UUID de `platform_users` (referencia lógica cross-base; sin FK Mongo entre bases) |
| `updated_by_user_id` | Opcional en MVP |

Entidades de solo append (p. ej. eventos): `created_at` obligatorio; sin `updated_at`.

## Aislamiento por tenant (invariante)

- Todo documento en **`gym_operational`** con datos de una empresa incluye **`tenant_id`**
  obligatorio y validado en capa dominio/aplicación.
- Documentos de **sucursal** incluyen **`tenant_id`** y **`branch_id`**.
- **Un índice compuesto con prefijo `tenant_id` no sustituye** el filtro obligatorio en
  cada lectura/escritura (ADR-0002). Los índices aceleran y refuerzan unicidad; la
  autorización y el scope vienen del repositorio y del contexto confiable.

## Normalización de correo (`email` vs `email_normalized`)

Cuando una entidad tenga dirección de correo **opcional u obligatoria**:

1. **`email`:** valor visible o capturado (puede conservar capitalización ingresada por el usuario).
2. **`email_normalized`:** presente **solo si hay correo**; derivado por reglas **deterministas**
   del backend antes de persistir e indexar:
   - recortar espacios en blanco al inicio y final;
   - convertir a minúsculas Unicode;
   - normalización Unicode **NFKC**;
   - rechazar cadenas vacías tras normalizar.
3. **No** documentar ni implementar equivalencias específicas de proveedores (p. ej. alias
   `+tag`, puntos en Gmail) en H1-A.2; cualquier regla adicional requiere ADR o decisión
   de producto explícita.
4. Búsquedas y unicidad usan **`email_normalized`**, no `email`.

### Índices únicos con correo opcional

Patrón recomendado (operational, unicidad por tenant):

```javascript
// Documentación ilustrativa — NO ejecutar en H1-A.2
{
  key: { tenant_id: 1, email_normalized: 1 },
  unique: true,
  partialFilterExpression: {
    email_normalized: { $exists: true, $type: "string" }
  }
}
```

- **Partial unique index** evita colisiones con documentos **sin** correo y evita el
  comportamiento ambiguo de `sparse` cuando el campo existe como `null`.
- Unicidad **global** de login en `platform_users`: índice único en `email_normalized`
  (base platform, sin `tenant_id`).

## Índices compuestos (catálogo propuesto)

Prefijo **`tenant_id`** en toda unicidad de negocio en operational. Ejemplos:

| Colección (conceptual) | Claves | Tipo |
|------------------------|--------|------|
| `branches` | `{ tenant_id: 1, branch_id: 1 }` | unique |
| `members` | `{ tenant_id: 1, member_id: 1 }` | unique |
| `members` | `{ tenant_id: 1, email_normalized: 1 }` | unique partial |
| `tenant_memberships` (platform) | `{ tenant_id: 1, user_id: 1 }` | unique |
| `platform_users` (platform) | `{ email_normalized: 1 }` | unique |

Índices de consulta (no unique): `{ tenant_id: 1, status: 1 }`, etc.

El catálogo ejecutable futuro vivirá en `database/README.md` (scripts en fase posterior).

## Agregaciones

- Primera etapa **`$match`** con `tenant_id` del contexto confiable.
- `$lookup`: pipelines que re-filtran por `tenant_id` compatible.

## Referencias

- [ADR-0002](../adr/0002-aislamiento-multiempresa.md)
- [ADR-0008](../adr/0008-dos-bases-mongodb-platform-operational.md)
- [TenantContext y repositorios](tenant-context-and-repositories.md)
- [Matriz de pruebas de aislamiento](tenant-isolation-test-matrix.md)

# ADR-0009: Modelo organizacional MVP (tenant, marca, sucursales)

- **Estado:** Accepted
- **Fecha:** 2026-10-14 (documentación H1-A.2)
- **Decisores:** Propietario del producto (decisión D2)

## Contexto

Gym ERP vende el ERP a **empresas** (tenants) que pueden operar **varias sucursales**.
En el mercado piloto (México, gimnasios tradicionales) muchas veces una empresa equivale
a una marca comercial visible. ADR-0002 exige `tenant_id` y `branch_id` cuando aplique.
ADR-0008 separa platform vs operational.

Este ADR fija el **modelo organizacional mínimo** para Release 0.1 sin aprobar aún RBAC
completo ni autenticación (ADR-0003 Proposed).

## Decisión

1. **Tenant (empresa cliente):** unidad de contrato SaaS y de **aislamiento de datos**
   (`tenant_id`). Documento principal en **`gym_platform`** (colección conceptual
   `tenants`).
2. **Marca comercial (MVP):** **una marca por tenant**, representada **inicialmente por
   campos del tenant** (p. ej. `display_name`, identificadores de branding futuros). **No**
   se crea entidad `brands` separada en MVP salvo ADR posterior.
3. **Sucursal (`branch`):** instalación física; **múltiples por tenant**. Vive en
   **`gym_operational`**, siempre con `tenant_id` y `branch_id`.
4. **Usuario de plataforma** y **membresía usuario–tenant** (`tenant_membership`): en
   **`gym_platform`**. Distinto del **socio** (`member`) del gimnasio en operational.
5. **Suscripción SaaS** de la empresa: metadatos en **`gym_platform`** (plan, estado,
   límites comerciales); sin facturación formal CFDI en 0.1 (ADR-0004).

## Roles iniciales (propuesta, no aprobada)

Para alinear diseño con Release 0.1, se **documenta como propuesta** — **no** es catálogo
definitivo de permisos (no ADR-0010):

| Rol (propuesto) | Intención |
|-----------------|-----------|
| `owner` | Control total del tenant; gestión de usuarios y configuración. |
| `admin` | Administración operativa; puede abarcar todas las sucursales. |
| `reception` | Operación diaria; **alcance opcional** restringido a `branch_ids` en membership. |

La resolución de permisos atómicos y matriz rol→permiso queda **pendiente** hasta
aprobar ADR-0003 y, en su momento, un ADR de RBAC.

## Ejemplo JSON ficticio

**Tenant (platform)**

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
  "legal_name": "Gimnasios Ficticios SA de CV",
  "display_name": "PowerGym",
  "status": "active",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-15T10:00:00Z"
}
```

**Sucursal (operational)**

```json
{
  "branch_id": "880e8400-e29b-41d4-a716-446655440030",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Sucursal Centro Ficticia",
  "timezone": "America/Mexico_City",
  "status": "active",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-15T10:00:00Z"
}
```

## Alternativas consideradas

- **Varias marcas por tenant en MVP:** pospuesto; requiere entidad `brands` y UX de selector.
- **Sucursal en platform:** descartado; datos operativos y check-in pertenecen a operational.
- **Tenant implícito sin documento platform:** descartado; onboarding y SaaS requieren registro.

## Consecuencias

- Toda feature operativa exige `tenant_id` + sucursal cuando el caso lo requiera.
- UI puede mostrar `display_name` del tenant como “marca” sin modelo extra en MVP.
- Evolución a multi-marca implica ADR de revisión, no extensión silenciosa.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Confundir membresía SaaS con membresía de socio | Nombres distintos en código y docs (`tenant_membership` vs `member_subscription`) |
| Cadena con varias marcas legales | Revisión post-piloto; ADR nuevo |
| Rol `reception` sin branch scope | Validar en `TenantContext` + tests (H1-B+) |

## Controles verificables

- Documentos de arquitectura H1-A coherentes con este ADR.
- Ninguna colección física creada en H1-A.2 (solo diseño).

## Condiciones de revisión

- Piloto con cadena multi-marca bajo una razón social.
- Requisito de franquicia con sub-tenants.

## Referencias

- [ADR-0002](0002-aislamiento-multiempresa.md)
- [ADR-0003](0003-autenticacion-sesiones.md) (Proposed)
- [ADR-0008](0008-dos-bases-mongodb-platform-operational.md)
- [TenantContext y repositorios](../architecture/tenant-context-and-repositories.md)

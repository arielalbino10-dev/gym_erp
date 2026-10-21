# Decisiones pendientes — autenticación (ADR-0003)

Registro H1-A.2, actualizado H2-C.2. **ADR-0003 está Accepted** (2026-10-19); login HTTP
gym/platform implementado (H2-B.7.2). Este documento conserva ítems de producto aún abiertos.

## Relación con multi-tenant (ya aprobado en ADR-0002 / H1-A.2)

Estas piezas **no** dependen de ADR-0003 para documentarse, pero **sí** para código HTTP:

- `tenant_id` confiable solo en servidor.
- Repositorios scoped y matriz T-01–T-15.
- Separación platform/operational (ADR-0008).

## Tabla de pendientes ADR-0003

| ID | Tema | Estado | Impacto en tenant / API |
|----|------|--------|-------------------------|
| P-01 | Aprobación global del ADR-0003 | **Accepted** | Auth MVP web en progreso |
| P-02 | TTL access y refresh | **Pendiente** | Duración de sesión y revalidación |
| P-03 | Access token: JWT vs opaco | **Pendiente** | Claims mínimos; no permisos en token |
| P-04 | SameSite Strict vs Lax; CSRF refresh/logout | **Pendiente** | Cookies web ERP |
| P-05 | Selector multi-tenant (usuario en N empresas) | **Pendiente** | Endpoint cambio tenant + persistencia `active_tenant_id` en sesión |
| P-06 | Política de contraseñas y MFA | **Pendiente** | ¿Release 0.1 o posterior? |
| P-07 | Topología dominios API vs web (CORS, cookies) | **Pendiente** | Despliegue |
| P-08 | Argon2id — librería concreta | **Pendiente** | Dependencia API |
| P-09 | Rate limit login | **Pendiente** | Endpoints auth |
| P-10 | IdP externo / SSO | **No decidido** | Fuera 0.1 |

## Comportamiento acordado documentalmente (H1-A.2, sin implementar)

Cuando ADR-0003 se apruebe e implemente:

1. Tras login, si el usuario tiene una sola membresía activa, fijar tenant en sesión.
2. Si tiene varias, UI de selección + endpoint servidor que valida membresía antes de
   fijar tenant (P-05).
3. Cada request de negocio reconstruye o valida `TenantContext` desde sesión/token +
   membership en DB; permisos **no** leídos del frontend.

Hasta entonces la API expone solo rutas acordadas sin tenant (p. ej. health).

## RBAC

Roles propuestos en [ADR-0009](../adr/0009-modelo-organizacional-mvp.md) (**no** catálogo
definitivo). Matriz permisos → **pendiente** ADR-0003 y futuro ADR RBAC.

## Referencias

- [ADR-0003](../adr/0003-autenticacion-sesiones.md) (Proposed)
- [TenantContext y repositorios](tenant-context-and-repositories.md)

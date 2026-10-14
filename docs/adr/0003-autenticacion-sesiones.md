# ADR-0003: Autenticación y sesiones

- **Estado:** Proposed
- **Fecha:** 2026-10-13 (documentación H0-A)
- **Decisores:** Propietario del producto (aprobación pendiente)

## Contexto

Release 0.1 es el ERP web para personal del gimnasio. Una app móvil (Expo) se
desarrollará después de validar pilotos. Las reglas exigen autenticación segura,
RBAC validado en backend, no exponer secretos y no confiar en permisos enviados
por el frontend.

H0-A no implementa autenticación; este ADR propone el diseño para aprobación antes de H1.

## Decisión (propuesta)

1. **Credenciales:** email + contraseña; hash con Argon2id (librería a autorizar en H0-B).
2. **Web (ERP):**
   - Access token de vida corta en **memoria** del cliente (Bearer).
   - Refresh token **opaco** en cookie `HttpOnly`, `Secure`, `SameSite` acotada, path
     restringido al endpoint de refresh.
   - **Rotación** del refresh en cada uso y **detección de reutilización** (revocar familia).
3. **Sesiones en servidor:** documentos en MongoDB (hash del refresh, usuario, tenant activo,
   expiración, revocación, metadatos `client_type` / `device_id` opcional para móvil futuro).
4. **Autorización:** permisos resueltos en **cada request** en el backend; el token no
   incluye permisos como fuente de verdad.
5. **Móvil (futuro):** mismos endpoints; refresh en almacenamiento seguro del dispositivo
   (Expo Secure Store), no en cookies. Detalle en ADR posterior al aprobar móvil.
6. Prohibido almacenar tokens en `localStorage` / `sessionStorage`.

## Alternativas consideradas

- **JWT en localStorage:** vulnerable a XSS; descartado.
- **Sesión opaca solo cookie (sin access token):** más simple para web; implica diseño distinto para móvil.
- **Proveedor IdP externo:** reduce carga de seguridad; costo y dependencia; no decidido.

## Consecuencias

- Revocación y logout efectivos vía servidor.
- Complejidad de cookies, CORS y CSRF en web.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| CSRF en refresh/logout | SameSite + verificación Origin + token anti-CSRF (pendiente elegir) |
| Rotación mal implementada | Tests dedicados en H1 |
| Dominios distintos API/web | Diseño de despliegue (mismo site o BFF); pendiente |

## Controles verificables

- Tests: login, refresh, rotación, reuso, logout, rate limit login (cuando existan).
- Auditoría de login exitoso/fallido (módulo audit).
- Ningún log con contraseñas, refresh ni access tokens.

## Condiciones de revisión

- Aprobación explícita del propietario de esta propuesta.
- Inicio de app móvil o requisito SSO/MFA.
- Cambio de topología de dominios en producción.

## Pendiente de aprobación

- TTL de access y refresh; tipo exacto de access token (JWT vs opaco).
- SameSite Strict vs Lax; mecanismo CSRF definitivo.
- Usuario con membresía en múltiples tenants (selector de tenant).
- Política de contraseñas y MFA (¿0.1 o posterior?).

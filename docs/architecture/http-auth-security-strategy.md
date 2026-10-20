# Estrategia de seguridad HTTP — autenticación (H2-B.6)

Preparación para H2-B.7+. **Sin rutas de login activas** en esta etapa.

## Cookies

| Cookie | Ámbito | Path | HttpOnly | Secure | SameSite |
|--------|--------|------|----------|--------|----------|
| `gym_platform_session` | Admin global | `/api/v1/platform` | sí | sí (prod) | Strict |
| `gym_session` | ERP gimnasio | `/api/v1` | sí | sí (prod) | Lax |
| `gym_platform_auth_cont` | Continuación MFA platform | `/api/v1/platform/auth` | sí | sí | Strict |

Constantes en `http_auth_contracts.py`. Platform y gym **no comparten** nombre ni path.

## CSRF

Mutaciones autenticadas por cookie: patrón **double-submit** (`gym_csrf` + header `X-CSRF-Token`).
Validar en handlers platform/gym antes de cambiar estado.
Métodos seguros: GET, HEAD, OPTIONS.

## Origin / Referer

En POST/PATCH/PUT/DELETE con cookie, comprobar `Origin` o `Referer` contra `CORS_ORIGINS` / allowlist ERP.

## Rate limiting

Límites lógicos documentados en `RateLimitPolicy` (IP, email, continuación MFA).
Implementación en middleware o reverse proxy en H2-B.7; pruebas de contrato en unit tests.

## Enumeración de usuarios

Respuestas uniformes (`AuthenticationFailedError`, tiempos similares vía Argon2 dummy hash).
No distinguir “email no existe” vs “contraseña incorrecta”.

## Cabeceras

`SecurityHeadersPolicy`: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`.
HTTPS terminado en proxy; API asume `Secure` cookies en producción.

## Continuidad MFA (server-side)

No reconstruir `VerifiedPrincipal` desde JSON del cliente.
Flujo: contraseña → `CreatePlatformAuthContinuationUseCase` → token opaco → MFA → sesión.
Ver `platform_auth_continuation.py` y colección `platform_auth_continuations`.

## MFA platform

`MFA_PLATFORM_ENCRYPTION_KEY` (base64, 32 bytes) obligatoria en producción.
Fail-closed si falta cifrado al componer `IdentityInfrastructure`.

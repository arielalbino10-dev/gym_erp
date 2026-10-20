# Estrategia de seguridad HTTP — autenticación (H2-B.6)

Preparación para H2-B.7+. **Sin rutas de login activas** en esta etapa.

## Cookies

| Cookie | Ámbito | Path | HttpOnly | Secure | SameSite |
|--------|--------|------|----------|--------|----------|
| `gym_erp_platform_session` | Admin global | `/api/v1/platform` | sí | sí (prod) | Strict |
| `gym_erp_gym_session` | ERP gimnasio | `/api/v1/gym` | sí | sí (prod) | Lax |
| `gym_erp_platform_auth_cont` | Continuación MFA platform | `/api/v1/platform/auth` | sí | sí | Strict |

Constantes en `http_auth_contracts.py`. Platform y gym **no comparten** nombre ni path.

## CSRF y perfiles de mutación (H2-B.7.1.1)

| Perfil | Cuándo | Origin (POST/…) | CSRF |
|--------|--------|-----------------|------|
| `PUBLIC` | Mutación sin cookies de sesión | Sí | No |
| `PRE_AUTHENTICATION` | Login / MFA antes de sesión | Sí | No salvo que la petición ya lleve cookie de sesión → **403** |
| `COOKIE_SESSION` | Logout, CRUD con sesión platform/gym | Sí | **Obligatorio** (`csrf_binding_key` + double-submit) |

Helpers: `enforce_public_mutation_security`, `enforce_pre_authentication_mutation_security`,
`enforce_cookie_session_mutation_security`. Si la petición incluye `gym_erp_platform_session`,
`gym_erp_gym_session` o `gym_erp_platform_auth_cont` y el handler no usa `COOKIE_SESSION`, se rechaza
(fail-closed ante omisión accidental).

Patrón **double-submit** (`gym_erp_csrf` + header `X-CSRF-Token`). Registro server-side en
`http_csrf_tokens` (hash SHA-256, binding por contexto — p. ej. `session:{id}` o
`continuation:{id}`, consumo único). Métodos seguros: GET, HEAD, OPTIONS.

## Origin / Referer

En POST/PATCH/PUT/DELETE con cookie, comprobar `Origin` o `Referer` contra `CORS_ORIGINS` / allowlist ERP.

## Rate limiting

Límites lógicos documentados en `RateLimitPolicy` (IP, email, continuación MFA).
Implementación H2-B.7.1: contadores atómicos en MongoDB (`http_rate_limit_counters`), HTTP 429 + `Retry-After`, fail-closed en rutas sensibles si el backend falla.

## Enumeración de usuarios

Respuestas uniformes (`AuthenticationFailedError`, tiempos similares vía Argon2 dummy hash).
No distinguir “email no existe” vs “contraseña incorrecta”.

## Cabeceras

`SecurityHeadersPolicy`: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`.
`Cache-Control: no-store` en respuestas bajo `/api/v1/platform` y `/api/v1/gym`.
HTTPS terminado en proxy; `TRUSTED_PROXY_IPS` + `X-Forwarded-Proto` solo desde peers de confianza.
`APP_ENV=production` rechaza `ALLOW_INSECURE_COOKIES=true`. `CORS_ORIGINS` sin comodines (credenciales).

## Continuidad MFA (server-side)

No reconstruir `VerifiedPrincipal` desde JSON del cliente.
Flujo: contraseña → `CreatePlatformAuthContinuationUseCase` → token opaco → MFA → sesión.
Ver `platform_auth_continuation.py` y colección `platform_auth_continuations`.

## MFA platform

`MFA_PLATFORM_ENCRYPTION_KEY` (base64, 32 bytes) obligatoria en producción.
Fail-closed si falta cifrado al componer `IdentityInfrastructure`.

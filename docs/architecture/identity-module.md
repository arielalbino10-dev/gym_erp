# Módulo Identity (H2-B.2)

Identidad humana **global** en `gym_platform` (ADR-0003). Sin tenant, roles ni sesiones HTTP en este incremento.

## UserIdentity

| Campo | Descripción |
|-------|-------------|
| `user_id` | UUID v4 estable |
| `email` / `email_normalized` | Visible recortado + normalización shared kernel |
| `status` | `pending_verification`, `active`, `locked`, `disabled` |
| `email_verified_at` | Obligatorio si `status=active` |
| `credential_version` | Entero ≥ 0; incremento en cambio de contraseña (futuro) |
| `created_at` / `updated_at` | UTC |

Transiciones: ver `IDENTITY_ALLOWED_TRANSITIONS` en `domain/enums.py`.

## Puertos (application)

- **`PasswordHasher`:** `hash`, `verify`, `needs_rehash`.
- **`IdentityRepository`:** contrato async para persistencia (Mongo en H2-B.3).

## Argon2id

Implementación: `Argon2PasswordHasher` + `Argon2PasswordConfig`.

Parámetros iniciales (sujetos a benchmark en hardware objetivo):

| Parámetro | Valor |
|-----------|-------|
| `time_cost` | 3 |
| `memory_cost_kib` | 65536 |
| `parallelism` | 4 |
| `hash_len` | 32 |
| `salt_len` | 16 |
| `max_time_cost` / `max_memory_cost_kib` / `max_parallelism` | 10 / 262144 / 8 (límites al verificar hashes almacenados) |

Tipo: **Argon2id** exclusivamente (`argon2-cffi`, `Type.ID`).

Activación desde `pending_verification`: solo `mark_email_verified` (no `transition_status` → `active`).

## Persistencia (H2-B.3) — `gym_platform`

| Colección | Contenido |
|-----------|-----------|
| `user_identities` | `UserIdentity` |
| `user_credentials` | hash Argon2id por `user_id` (1:1) |
| `auth_sessions` | hash SHA-256 del token opaco; sin token plano |

Índices: `email_normalized` único; `user_id` único en credenciales; `token_hash` único;
`(user_id, session_kind)`; TTL en `expires_at` solo limpieza (expiración validada en dominio).

Concurrencia optimista vía `updated_at` (identidad/credencial) y `last_seen_at` (touch sesión).

Repositorios: `MongoIdentityRepository`, `MongoCredentialRepository`, `MongoAuthSessionRepository`.

## Casos de uso internos (H2-B.4)

- `CredentialVerificationService` — email/contraseña, Argon2id en `asyncio.to_thread`, dummy hash
  si la cuenta no existe.
- `CreateGymSessionUseCase` / `CreatePlatformSessionUseCase`.
- **Platform (H2-B.5):** sesión solo tras `PlatformMfaSessionAuthorization` consumida de forma
  atómica; sin repositorio de autorizaciones → `PlatformSessionEmissionDisabledError`.
- `ResolveSessionUseCase`, `RevokeSessionUseCase`, `RevokeAllUserSessionsUseCase`.

**Sin HTTP, cookies, CSRF ni rate limit** en esta etapa.

## MFA TOTP platform (H2-B.5) — `gym_platform`

| Colección | Contenido |
|-----------|-----------|
| `platform_mfa_totp_enrollments` | Secreto TOTP cifrado (AES-256-GCM), estado pending/enabled/disabled |
| `platform_mfa_challenges` | Desafíos de vida corta; consumo atómico |
| `platform_mfa_totp_steps` | Pasos TOTP usados (anti-replay); TTL solo limpieza |
| `platform_mfa_session_authorizations` | Autorización de un solo uso para emitir sesión platform |

Flujo interno: contraseña → `VerifiedPrincipal` (con `verified_at`) → desafío MFA
(solo con prueba de contraseña reciente, TTL 5 min) → verificación TOTP → autorización →
`CreatePlatformSessionUseCase(authorization_id=…)`.

Cifrado en reposo: `AesGcmMfaSecretEncryptor` (byte de versión de clave + nonce + ciphertext).
La clave vive fuera de MongoDB (config/env en despliegue; clave de prueba solo en tests).

`PlatformMfaVerificationTicket` queda obsoleto para sesión; no sustituye autorización persistida.

Casos de uso: `BeginPlatformTotpEnrollmentUseCase`, `ConfirmPlatformTotpEnrollmentUseCase`,
`StartPlatformMfaChallengeUseCase`, `VerifyPlatformMfaChallengeUseCase`.

## Fuera de alcance (H2-B.5)

Login/logout HTTP, cookies, RBAC, TenantContext, endpoints HTTP, usuarios root reales.

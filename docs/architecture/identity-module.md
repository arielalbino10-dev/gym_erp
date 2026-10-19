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
- **Platform (H2-B.4.1):** emisión bloqueada por defecto (`HardDisabledPlatformSessionEmission`);
  el ticket MFA no es prueba criptográfica hasta H2-B.5.
- `ResolveSessionUseCase`, `RevokeSessionUseCase`, `RevokeAllUserSessionsUseCase`.

**Sin HTTP, cookies, CSRF, rate limit ni MFA real** (puerto `PlatformMfaVerificationPort` +
`UnconfiguredPlatformMfaVerification` hasta H2-B.5).

## Fuera de alcance (H2-B.4)

Login/logout HTTP, cookies, RBAC, TenantContext, endpoints HTTP.

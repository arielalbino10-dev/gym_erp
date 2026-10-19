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

## Fuera de alcance (H2-B.2)

Login/logout, cookies, sesiones opacas, MFA, recuperación de cuenta, RBAC, endpoints HTTP, repositorios MongoDB.

# ADR-0003: Autenticación y sesiones

- **Estado:** Accepted
- **Fecha inicial:** 2026-10-13 (documentación H0-A)
- **Última revisión documental:** 2026-10-19 (H2-B.1.1 — consolidación autenticación propia MVP web)
- **Fecha de aprobación:** 2026-10-19 (propietario — H2-B.2)
- **Decisores:** Propietario del producto
- **Relacionado:** [ADR-0008](0008-dos-bases-mongodb-platform-operational.md) (Accepted),
  [ADR-0009](0009-modelo-organizacional-mvp.md) (Accepted),
  [ADR-0010](0010-organization-onboarding-idempotencia.md) (Proposed),
  diseño H2-A / H2-A.1 / H2-B.1; núcleo identity H2-B.2 (dominio + Argon2id, sin sesiones HTTP)

## Contexto

Gym ERP es un SaaS B2B multi-tenant: operadores de plataforma (`root_admin`, `platform_admin`),
gimnasios clientes (tenants) con usuarios operativos (`gym_owner`, `gym_admin`, roles custom y
alcance por sucursal). Release 0.1 prioriza el **ERP web** (React + Vite); móvil es posterior.

Las reglas del proyecto exigen autenticación segura, RBAC validado en backend, no exponer secretos
y **no confiar** en `tenant_id`, `branch_id`, roles ni permisos enviados por el frontend.

H0-A documentó autenticación sin implementarla. H1 no añadió auth HTTP (solo health). H2-B.1 analizó
**autenticación propia** como candidata MVP web, con migración futura posible vía adaptador OIDC.
Esta revisión **consolida** ese diseño y **sustituye** para el MVP web el modelo Bearer + refresh
descrito en la revisión H0-A (ver historial abajo).

## Historial de decisiones (conservado)

### Revisión H0-A (2026-10-13) — superseded para MVP web

1. Credenciales: email + contraseña; hash Argon2id (librería a autorizar).
2. Web: **access token** de vida corta en memoria (Bearer) + **refresh token opaco** en cookie
   HttpOnly con rotación y detección de reutilización.
3. Sesiones en MongoDB (hash del refresh, usuario, tenant activo, revocación).
4. Autorización en cada request; token no es fuente de verdad de permisos.
5. Prohibido `localStorage` / `sessionStorage` para tokens.

**Motivo de cambio (H2-B.1.1):** menor superficie criptográfica propia, revocación inmediata sin
familia refresh, alineación con cookies únicas y módulo `identity` desacoplado de `access`. El
modelo Bearer + refresh **permanece alternativa válida** para cliente móvil futuro (ADR aparte).

## Decisión (Accepted — revisión H2-B.1.1)

### 1. Credenciales e identidad

1. **Identidad global** (`UserIdentity`) en **gym_platform**, independiente de memberships tenant.
2. **Email + contraseña** para MVP; hash **Argon2id** (`argon2-cffi` en `apps/api`; núcleo
   `Argon2PasswordHasher` en H2-B.2).
3. Política de contraseña orientada a NIST SP 800-63B: mínimo **12** caracteres; bloqueo de listas
   comunes (implementación progresiva).
4. **Verificación de correo** obligatoria antes de activar cuentas operativas (invitaciones gym);
   recomendada para cuentas platform.
5. **Primer `root_admin`:** bootstrap **solo** vía procedimiento operativo controlado (CLI one-shot
   o invitación offline); **prohibido** registro público privilegiado, credenciales compartidas o
   contraseñas en repositorio.
6. **Adaptador `IdentityProviderAdapter`:** contrato para OIDC/IdP futuro; MVP implementa modo
   `local` únicamente.

### 2. Sesiones opacas server-side (MVP web)

1. **No JWT propio** ni access Bearer en memoria para el MVP web salvo justificación posterior
   aprobada.
2. Tras autenticación exitosa (+ MFA cuando aplique), el servidor emite un **token opaco**
   (≥ 32 bytes CSPRNG); la cookie transporta el token plano **una sola vez**; en MongoDB se
   almacena **solo** hash (p. ej. SHA-256 del token).
3. Documentos **`auth_sessions`** en **gym_platform** (nombre lógico): `user_id`, `session_kind`,
   `active_tenant_id` (solo gym), expiración absoluta, inactividad, revocación, metadatos de
   auditoría, indicador MFA/step-up según §5.
4. **Dos superficies de sesión** (cookies separadas):
   - `session_kind=platform` — panel operador SaaS.
   - `session_kind=gym` — panel del gimnasio (tenant).
5. **Session fixation:** en login exitoso siempre **nueva** sesión; no reutilizar id/token
   pre-autenticación enviado por el cliente.
6. **Revocación:** logout (sesión actual), logout global (por `user_id` y/o `session_kind`),
   cambio/recuperación de contraseña (todas las sesiones), cambios material de roles/membership
   (invalidación vía `authz_epoch` — ver §8).
7. Prohibido almacenar tokens de sesión en `localStorage` / `sessionStorage`.

### 3. Topología SPA / API, cookies y HTTPS

**Recomendación MVP (mismo sitio lógico):**

| Entorno | SPA | API | Notas |
|---------|-----|-----|--------|
| Desarrollo | `http://127.0.0.1:5173` | `http://127.0.0.1:8000` | CORS + `credentials`; cookies **Secure=false** solo en dev explícito |
| Producción (recomendado) | `https://app.<dominio>` | `https://app.<dominio>/api` **vía reverse proxy** (mismo site) | Preferible a API en subdominio distinto |

**Nombres de cookie (propuesta):**

| Cookie | `session_kind` | Path (prod mismo-site) |
|--------|----------------|-------------------------|
| `gym_erp_platform_session` | platform | `/api/v1/platform` o `/` si BFF unificado |
| `gym_erp_gym_session` | gym | `/api/v1/gym` o `/` |

**Atributos obligatorios en producción:**

- `HttpOnly`: **siempre**.
- `Secure`: **siempre** en producción (HTTPS).
- `SameSite`:
  - **`Strict`** si SPA y API comparten **origen** (proxy `/api` → FastAPI) — **recomendado MVP**.
  - **`Lax`** solo si API vive en subdominio distinto **y** se documenta CSRF reforzado; requiere
    aprobación explícita del propietario.

**Domain:** omitir atributo `Domain` en MVP mismo-site; si subdominios compartidos, usar
`.dominio` con análisis CSRF explícito.

**CORS:** `allow_credentials=True` con lista **explícita** de orígenes (como hoy en Settings);
nunca `*` con credenciales.

**HTTPS:** obligatorio en producción; HSTS en edge (infra, fuera de este ADR).

### 4. Protección CSRF (obligatoria desde el primer endpoint con cookie)

Todo endpoint **mutante** (`POST`, `PUT`, `PATCH`, `DELETE`) que acepte autenticación por cookie
**debe** validar CSRF **antes** de lógica de negocio.

**Mecanismo propuesto (MVP):** **double-submit cookie** + verificación **`Origin`/`Referer`**
cuando el navegador los envíe:

1. En login/MFA exitoso (sesión plena), el servidor emite cookie **`gym_erp_csrf`** (no HttpOnly,
   `SameSite` acorde a sesión, `Secure` en prod) con token aleatorio; el cliente envía el mismo
   valor en header **`X-CSRF-Token`** en mutaciones.
2. El servidor compara header vs cookie y rechaza si mismatch (**403**).
3. **`GET`/`HEAD`/`OPTIONS`** no exigen CSRF; no deben tener efectos secundarios.
4. Tests de integración CSRF son **criterio de salida** de H2-B.2 (primera ruta mutante con cookie).

**Alternativa descartada para MVP:** confiar solo en `SameSite` sin token — insuficiente para
Lax/subdominios y logout CSRF.

### 5. Estado provisional pre-MFA (platform)

1. Tras password válido en login **platform**, si MFA no está satisfecho, la sesión queda en estado
   **`mfa_pending`** (documento `auth_sessions` o flag equivalente).
2. Cookies **`mfa_pending`**:
   - **No** autorizan ningún endpoint `/api/v1/platform/*` excepto rutas explícitas de enrolamiento
     y verificación MFA (`/auth/mfa/*`).
3. **Sin permisos operativos** ni de plataforma en este estado; `AuthorizationService` no se invoca
   para acciones administrativas.
4. Tras MFA OK, transición a sesión **`active`**, rotación de token opaco (anti-fixation), emisión
   CSRF token.
5. Login **gym** puede usar flujo análogo si MFA gym se exige en fases posteriores; MVP platform
   es el gate crítico.

### 6. Recuperación MFA — `root_admin` (sin bypass público)

1. **Prohibido** endpoint público “reset MFA” autoservicio para `root_admin`.
2. Recuperación solo vía:
   - Segundo **`root_admin`** existente que revoque factors del primero (con auditoría), o
   - Procedimiento **offline** documentado (break-glass) con registro en audit log platform.
3. **`platform_admin`:** reset MFA por `root_admin` o procedimiento delegado auditado.
4. Cualquier ruta de enrolamiento MFA exige sesión `mfa_pending` o step-up reciente; **no** query
   params con secretos en URL persistentes.

### 7. XSS, CSP y acciones autenticadas maliciosas

| Control | Requisito |
|---------|-----------|
| **HttpOnly cookies** | Token de sesión inaccesible desde JS |
| **CSP** (producción) | Política restrictiva en SPA: `default-src 'self'`; scripts sin `unsafe-inline` donde sea viable; report-only previo a enforce |
| **No tokens en JS** | Sin Bearer en memoria SPA para MVP |
| **CSRF** | §4 |
| **Sanitización** | React por defecto; prohibir `dangerouslySetInnerHTML` salvo excepción revisada |
| **Step-up MFA** | Operaciones sensibles platform (aprobar solicitudes, cambiar roles) exigen MFA verificado en ventana ≤ **5 min** (configurable) |

**Riesgo residual:** XSS en SPA puede abusar sesión same-site (requests con cookie automática).
Mitigación: CSP estricta + CSRF en mutaciones + minimizar superficie XSS.

### 8. Autorización separada de autenticación

1. Módulo **`identity`:** autentica, mantiene sesión, MFA, credenciales.
2. Módulo **`access`** (H2-C): autoriza — memberships, roles, permisos, `branch_scope_mode`,
   estado tenant/subscription SaaS.
3. **`TenantContext`** se construye **solo** en backend tras `SessionResolver` + `AuthorizationService`.
4. **Los permisos efectivos no se almacenan en cookie** ni como autoridad inmutable en sesión; como
   mucho `authz_epoch` / hints para detectar sesiones obsoletas — **siempre** re-resolver permisos
   en cada request protegido.
5. React envía solo recursos de UI; **`tenant_id` / `branch_id` / roles en body o query no son
   fuente de verdad**.

### 9. Expiración, inactividad y revocación (configurables)

Parámetros en **`Settings`** (env), con valores **iniciales propuestos** y tests que validen
comportamiento (no valores hardcodeados dispersos):

| Parámetro | Valor inicial propuesto | Justificación |
|-----------|-------------------------|---------------|
| `SESSION_PLATFORM_ABSOLUTE_TTL` | 12 h | Jornada admin platform |
| `SESSION_GYM_ABSOLUTE_TTL` | 8 h | Turno operativo |
| `SESSION_PLATFORM_IDLE_TTL` | 15 min | Reduce riesgo panel admin desatendido |
| `SESSION_GYM_IDLE_TTL` | 30 min | UX recepción vs seguridad |
| `SESSION_TOUCH_THROTTLE` | 60 s | Limitar writes Mongo en `last_seen_at` |
| `MFA_STEP_UP_MAX_AGE` | 5 min | Operaciones sensibles platform |
| `CSRF_TOKEN_TTL` | Igual que sesión | Rotación con sesión |

Revocación masiva al: logout, password change/reset, `credential_version++`, revocación admin,
 mismatch de `authz_epoch`.

### 10. MFA platform (obligatorio)

- **`root_admin`** y **`platform_admin`:** MFA (**TOTP** MVP; WebAuthn fase posterior) **obligatorio**
  antes de sesión platform `active`.
- Sin MFA enrolado: solo rutas de enrolamiento + logout.

### 11. Móvil (futuro — fuera MVP web)

- No cookies; sesión opaca en header o tokens gestionados por IdP; ADR complementario cuando se
  apruebe móvil. El modelo H0-A Bearer + refresh **puede reevaluarse** entonces.

## Alternativas consideradas (revisión H2-B.1.1)

| Alternativa | Decisión |
|-------------|----------|
| JWT en localStorage | Descartado (XSS). |
| Bearer + refresh (H0-A) | **Superseded para MVP web**; candidato móvil. |
| Sesión opaca solo cookie | **Adoptada MVP web**. |
| IdP gestionado (OIDC) primario | Pospuesto; **adapter** preparado, no bloquea MVP local. |
| Una sola cookie para platform+gym | Descartado; mezcla superficies y amplía blast radius. |
| CSRF solo SameSite | Descartado; insuficiente como control único. |
| Permisos embebidos en sesión/JWT | Descartado; conflicto con RBAC dinámico y roles custom. |

## Consecuencias

- Revocación y logout **inmediatos** vía servidor.
- Complejidad en cookies, CORS, CSRF y despliegue same-site.
- Dos cookies de sesión + cookie CSRF: más coordinación en frontend (`credentials: 'include'`,
  header CSRF en mutaciones).
- Tests de seguridad HTTP obligatorios desde H2-B.2.
- ADR **Accepted** (2026-10-19) como contrato estable para diseño e implementación progresiva.

## Riesgos y mitigaciones

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| XSS roba sesión / CSRF token no HttpOnly | Alta | CSP; CSRF solo en mutaciones; HttpOnly en sesión |
| CSRF en cookie auth | Alta | §4 desde primer POST autenticado |
| Confusión tenant en SPA | Crítica | TenantContext solo backend; tests negativos |
| Argon2 DoS | Media | Rate limit login; benchmark params |
| Enumeración cuentas | Media | Respuestas genéricas login/reset |
| Despliegue API/SPA cross-site mal configurado | Alta | Same-site proxy recomendado; checklist prod |
| MFA bypass por rutas olvidadas | Alta | Middleware uniforme platform; tests |
| Homónimo PyMongo `session` vs auth session | Media | Naming `AuthSession` en docs/código futuro |

## Controles verificables

- Tests unitarios: Argon2 hash/verify/rehash; generación token; hash almacenado.
- Tests integración: login/logout; sesión expirada/revocada; fixation; password change revoca sesiones.
- Tests HTTP seguridad: CSRF fail/pass; Origin inválido; cookie platform no accede gym API.
- Tests MFA: platform sin MFA → 401 en `/platform/*`; bypass imposible.
- Auditoría: login ok/fail, MFA enroll/verify, revocación MFA admin, bootstrap root.
- **Ningún log** con contraseña, token opaco plano, CSRF ni secretos TOTP.

## Requisitos mínimos antes de endpoints platform en **producción**

No habilitar en producción rutas `/api/v1/platform/*` con efecto real (listar/aprobar solicitudes,
administrar clientes, etc.) hasta cumplir **todos**:

1. ADR-0003 **Accepted** por propietario.
2. MFA obligatorio operativo para roles platform.
3. CSRF en todos los mutantes con cookie.
4. Rate limiting login / reset / MFA.
5. Bootstrap `root_admin` completado sin credenciales en repo.
6. Módulo **`access`** (H2-C) con autorización en al menos un endpoint platform de prueba.
7. Audit log platform append-only para acciones sensibles.
8. HTTPS + `Secure` cookies + CSP enforce en SPA.
9. Suite tests §Controles verificables en CI (integración auth donde aplique).
10. Runbook recuperación MFA root (§6) documentado y probado en staging.

**Desarrollo local:** se permiten endpoints auth/platform en staging con flags explícitos
(`APP_ENV=development`) sin sustituir esta lista para producción.

## Condiciones de revisión

- Aprobación explícita del propietario (**Proposed → Accepted**).
- Cambio a IdP primario u otro modelo móvil.
- Topología de dominios distinta (subdominios API vs app).
- Incidente de seguridad o auditoría externa.

## Pendiente de aprobación del propietario (condiciones operativas)

- Same-site proxy vs API subdominio (`SameSite` Lax) en despliegue concreto.
- Valores numéricos §9 (TTL) en producción.
- Mecanismo bootstrap root definitivo (CLI vs invitación).
- MFA obligatorio para `gym_owner` en piloto comercial.
- Proveedor de email transaccional.

**Resuelto en aprobación H2-B.2:** autenticación propia con **sesión opaca** MVP web; dependencia
`argon2-cffi` autorizada.

## Implementación parcial (H2-B.2)

Entregado en código (sin endpoints HTTP):

- Dominio `UserIdentity` y estados en `modules/identity/domain/`.
- Puertos `PasswordHasher` e `IdentityRepository` (sin Mongo).
- `Argon2PasswordHasher` (Argon2id) y parámetros centralizados.
- Pruebas unitarias de dominio y hashing.

**No implementado aún:** login/logout, cookies, sesiones, CSRF, MFA, recuperación, RBAC/access,
persistencia identity, bootstrap root.

---

## Criterios de aceptación para iniciar **H2-B.2** (implementación)

H2-B.2 puede comenzar cuando:

1. Este ADR permanece **Proposed** pero el propietario **no objeta** la revisión H2-B.1.1 por escrito, **o** ADR pasa a **Accepted**.
2. Equipo acordó topología dev (CORS actual + plan same-site prod).
3. Lista de puertos/contratos `identity` alineada con este ADR (H2-B.1).
4. Riesgos CRITICAL/HIGH de H2-B.1 reconocidos en backlog (CSRF, XSS/CSP, tenant trust).

H2-B.2 **no** debe exponer endpoints platform administrativos reales hasta cumplir §Requisitos mínimos producción.

---

## Confirmación de alcance H2-B.1.1

Esta revisión **solo modifica documentación** (`docs/adr/0003-autenticacion-sesiones.md`).
**No** se alteraron módulos funcionales Python/React, dependencias, endpoints, colecciones MongoDB,
usuarios ni credenciales.

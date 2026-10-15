# Estructura del monorepositorio

Documento de referencia. **H0-B/C:** esqueleto API/web y CI. **H1-A.2:** arquitectura
multi-tenant documentada. **H1-B/C:** núcleo scoped MongoDB. **H1-D:** módulo
**organization** (dominio, repos, UoW, CreateOrganization interno).

```text
gym_erp/
├── .cursor/rules/              # Reglas Cursor
├── .github/workflows/          # CI (unit tests API, sin MongoDB)
├── apps/
│   ├── api/                    # FastAPI, paquete gym_erp_api
│   ├── web/                    # React + Vite .jsx
│   └── mobile/                 # Expo .jsx — reservado (ADR-0005)
├── packages/                   # JS compartido opcional — posterior
├── database/                   # README + índices futuros
├── infra/
│   └── compose/                # MongoDB local (replica set)
├── docs/
│   ├── adr/
│   ├── architecture/
│   └── development/
├── .env.example                # Valores ficticios (raíz)
├── .gitignore
└── README.md
```

## apps/api

```text
apps/api/
├── pyproject.toml
├── uv.lock
├── src/gym_erp_api/
│   ├── main.py
│   ├── core/                   # config
│   ├── infrastructure/mongo/ # MongoDatabases, scoped repo, UoW (H1-D)
│   ├── shared_kernel/          # TenantContext, identifiers
│   ├── presentation/api_v1/    # health (único router público H1-D)
│   └── modules/
│       ├── organization/       # H1-D — ver organization-module.md
│       ├── identity/           # reservado
│       ├── access_control/     # reservado
│       ├── members/
│       └── …
└── tests/
    ├── unit/
    │   ├── modules/organization/
    │   └── infrastructure/
    ├── integration/
    │   ├── tenant_isolation/   # H1-C
    │   └── organization/       # H1-D (Mongo manual)
    └── support/                # fixtures, integration_environment
```

### modules/organization (implementado H1-D)

```text
modules/organization/
├── domain/                 # Tenant, Branch, validators
├── application/
│   ├── commands/           # CreateOrganizationCommand
│   ├── ports/              # repos, idempotency, UoW factory
│   ├── use_cases/          # CreateOrganizationHandler
│   ├── policies/           # TenantOperationalPolicy
│   └── authorization/      # scopes internos (no HTTP auth)
└── infrastructure/mongo/   # mappers + Platform*/Operational* repos
```

Detalle: [organization-module.md](organization-module.md).

## apps/web

```text
apps/web/
├── package.json
├── vite.config.js
└── src/
    ├── app/
    ├── features/
    ├── components/
    └── lib/
```

## Reglas

- No acceso directo a MongoDB desde frontends.
- No duplicar reglas de negocio en `apps/web` ni `apps/mobile`.
- Cambios de límites entre módulos → ADR aprobado.
- Organization **sin** endpoints HTTP en H1-D (ADR-0010 Proposed).

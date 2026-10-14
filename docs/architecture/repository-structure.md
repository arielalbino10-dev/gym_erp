# Estructura del monorepositorio (prevista)

Documento de referencia. **H0-A** crea solo `docs/` y archivos raíz de documentación.
Las carpetas de aplicaciones se crearán en **H0-B** y siguientes fases.

```text
gym_erp/
├── .cursor/rules/              # Reglas Cursor (existente)
├── .github/workflows/          # CI — H0-C (no creado en H0-A)
├── apps/
│   ├── api/                    # FastAPI, paquete gym_erp_api — H0-B+
│   ├── web/                    # React + Vite .jsx — H0-B+
│   └── mobile/                 # Expo .jsx — reservado (ADR-0005)
├── packages/                   # JS compartido opcional — posterior
├── database/                   # Índices, seeds, migraciones — posterior
├── infra/
│   └── compose/                # MongoDB local (existente)
├── docs/
│   ├── adr/
│   ├── architecture/
│   └── product/
├── .env.example                # Valores ficticios (raíz)
├── .gitignore
└── README.md
```

## apps/api (futuro)

```text
apps/api/
├── pyproject.toml
├── uv.lock
├── src/gym_erp_api/
│   ├── main.py
│   ├── bootstrap/              # config, lifespan, middlewares
│   ├── shared_kernel/          # mínimo: IDs, TenantContext, errores
│   ├── api_v1/
│   └── modules/
│       ├── identity/
│       ├── access_control/
│       ├── organization/
│       ├── members/
│       ├── catalog/
│       ├── memberships/
│       ├── payments/
│       ├── attendance/
│       └── audit/
└── tests/
    ├── unit/
    ├── integration/
    └── tenant_isolation/
```

## apps/web (futuro)

```text
apps/web/
├── package.json
├── vite.config.js
└── src/
    ├── app/                    # router, providers, guards UI
    ├── features/               # por dominio funcional
    ├── components/
    └── lib/                    # api client, formatters
```

## Reglas

- No acceso directo a MongoDB desde frontends.
- No duplicar reglas de negocio en `apps/web` ni `apps/mobile`.
- Cambios de límites entre módulos → ADR aprobado.

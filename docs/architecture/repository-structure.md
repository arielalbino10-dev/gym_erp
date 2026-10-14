# Estructura del monorepositorio

Documento de referencia. **H0-B/C** implementaron esqueleto API/web y CI; **H1-A.2**
formalizó arquitectura multi-tenant en `docs/adr/0008`, `0009` y
`docs/architecture/multi-tenant-data-conventions.md` y documentos relacionados (sin código de negocio aún).

```text
gym_erp/
├── .cursor/rules/              # Reglas Cursor (existente)
├── .github/workflows/          # CI — H0-C (no creado en H0-A)
├── apps/
│   ├── api/                    # FastAPI, paquete gym_erp_api — H0-B+
│   ├── web/                    # React + Vite .jsx — H0-B+
│   └── mobile/                 # Expo .jsx — reservado (ADR-0005)
├── packages/                   # JS compartido opcional — posterior
├── database/                   # README + índices futuros (H1-A.2: solo docs)
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

## apps/api (objetivo modular; parcialmente implementado en H0-B)

```text
apps/api/
├── pyproject.toml
├── uv.lock
├── src/gym_erp_api/
│   ├── main.py                 # existente (H0-B)
│   ├── core/                   # config (H0-B)
│   ├── bootstrap/              # lifespan, middlewares — H1-B+
│   ├── shared_kernel/          # TenantContext, errores — H1-B+ (ver docs H1-A)
│   ├── presentation/api_v1/    # existente (health)
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
    ├── integration/            # existente (H0-C)
    ├── tenant_isolation/       # planificado (H1-B+; ver matriz H1-A)
    └── test_*.py               # unitarias actuales
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

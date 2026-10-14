# Gym ERP Web

ERP administrativo React + Vite (`.jsx`). H0-B: pantalla de estado de la API.

## Setup

```bash
npm install
```

Opcional: `VITE_API_BASE_URL` en `.env` (ver raíz `.env.example`). En desarrollo, Vite
proxifica `/api` hacia `http://127.0.0.1:8000`.

## Scripts

```bash
npm run dev      # http://127.0.0.1:5173
npm run lint
npm run build
```

En CI (GitHub Actions): `npm ci`, `npm run lint`, `npm run build`. Ver
[docs/development/ci.md](../../docs/development/ci.md).

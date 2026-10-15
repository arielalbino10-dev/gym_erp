# Datos demostrativos (Gym ERP Web)

Estos módulos **no** son fuente operativa ni sustituyen la API FastAPI.

## Reglas

- No importar datos demo en código que persista o envíe información al backend.
- No usar `tenant_id`, `branch_id` ni credenciales como autorización.
- Etiquetar siempre la UI con indicadores de demostración visibles.
- Cuando exista ADR-0003, los datos reales vendrán de `/api/v1` con sesión validada en servidor.

## Archivos

| Archivo | Uso |
|---------|-----|
| `dashboard.demo.js` | KPIs, actividad, membresías, acciones rápidas |
| `attendance.demo.js` | Serie diaria de asistencias (determinista) |

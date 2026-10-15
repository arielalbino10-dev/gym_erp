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
| `branches.demo.js` | Catálogo único de sucursales ficticias (`branchId`, código, estado) |
| `members.demo.js` | Socios seed (referencia `branchId` del catálogo) |
| `memberships.demo.js` | Planes y asignaciones (heredan sucursal del socio) |
| `attendance-records.demo.js` | Check-ins individuales demo |

El selector global de sucursal (`DemoUiPreferencesProvider`) filtra la interfaz en memoria; **no** es control de seguridad.

| `organization.demo.js` | Perfil de empresa y metadatos de producto (UI-01.7) |

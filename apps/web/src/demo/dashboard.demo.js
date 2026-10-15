/** KPIs, actividad y resúmenes — exclusivamente demostración. */

export const DEMO_KPI_METRICS = [
  {
    id: "active-members",
    title: "Socios activos",
    value: "128",
    footnote: "Ilustrativo · no operativo",
  },
  {
    id: "active-memberships",
    title: "Membresías vigentes",
    value: "112",
    footnote: "Incluye planes demo",
  },
  {
    id: "attendance-today",
    title: "Asistencias de hoy",
    value: "118",
    footnote: "Coincide con el último día del gráfico demo",
  },
  {
    id: "revenue-month",
    title: "Ingresos del mes",
    value: "$12,450",
    footnote: "MXN ficticios · sin reglas de negocio",
  },
];

export const DEMO_RECENT_ACTIVITY = [
  {
    id: "act-1",
    time: "10:42",
    dateIso: "2026-10-15",
    text: "Check-in demo — Socio ficticio 14 (plan mensual)",
    kind: "attendance",
    branchId: "demo-branch-centro",
  },
  {
    id: "act-2",
    time: "09:15",
    dateIso: "2026-10-15",
    text: "Renovación demo — membresía trimestral",
    kind: "membership",
    branchId: "demo-branch-norte",
  },
  {
    id: "act-3",
    time: "Ayer",
    dateIso: "2026-10-14",
    text: "Alta demo de socio — recepción centro",
    kind: "member",
    branchId: "demo-branch-centro",
  },
  {
    id: "act-4",
    time: "Ayer",
    dateIso: "2026-10-14",
    text: "Asistencia grupal demo — clase funcional",
    kind: "attendance",
    branchId: "demo-branch-sur",
  },
  {
    id: "act-5",
    time: "12 oct",
    dateIso: "2026-10-12",
    text: "Membresía demo vencida (ejemplo ilustrativo)",
    kind: "membership",
    branchId: "demo-branch-norte",
  },
];

export const DEMO_MEMBERSHIP_SUMMARY = [
  { id: "plan-monthly", plan: "Mensual", active: 86, expiringSoon: 4 },
  { id: "plan-quarterly", plan: "Trimestral", active: 19, expiringSoon: 1 },
  { id: "plan-annual", plan: "Anual", active: 7, expiringSoon: 0 },
];

export const DEMO_QUICK_ACTIONS = [
  { id: "qa-members", label: "Ir a Socios", to: "/socios", description: "Listado demo futuro" },
  {
    id: "qa-memberships",
    label: "Ir a Membresías",
    to: "/membresias",
    description: "Planes ilustrativos",
  },
  {
    id: "qa-attendance",
    label: "Ir a Asistencias",
    to: "/asistencias",
    description: "Check-ins de ejemplo",
  },
  {
    id: "qa-branches",
    label: "Ir a Sucursales",
    to: "/sucursales",
    description: "Vista multi-sucursal demo",
  },
];

/** Retraso simulado de carga inicial del dashboard (ms). */
export const DEMO_DASHBOARD_LOAD_MS = 450;

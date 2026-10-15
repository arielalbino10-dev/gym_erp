/**
 * Planes comerciales (catálogo) y membresías asignadas a socios ficticios.
 * Importes ilustrativos; no operativos.
 */

import {
  DEMO_MEMBERS,
  DEMO_REFERENCE_DATE,
  MEMBERSHIP_TYPES,
  MEMBER_STATUS,
} from "./members.demo.js";

export { DEMO_REFERENCE_DATE };

/** Días antes del vencimiento para marcar "próxima a vencer". */
export const EXPIRING_SOON_DAYS = 14;

export const MEMBERSHIP_LIFECYCLE = {
  ACTIVE: "vigente",
  EXPIRED: "vencida",
  EXPIRING: "por_vencer",
  SUSPENDED: "suspendida",
};

export const LIFECYCLE_FILTER_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: MEMBERSHIP_LIFECYCLE.ACTIVE, label: "Vigente" },
  { value: MEMBERSHIP_LIFECYCLE.EXPIRING, label: "Próxima a vencer" },
  { value: MEMBERSHIP_LIFECYCLE.EXPIRED, label: "Vencida" },
  { value: MEMBERSHIP_LIFECYCLE.SUSPENDED, label: "Suspendida (demo)" },
];

export const PLAN_FILTER_OPTIONS = [
  { value: "", label: "Todos los planes" },
  { value: MEMBERSHIP_TYPES.MONTHLY, label: "Mensual" },
  { value: MEMBERSHIP_TYPES.QUARTERLY, label: "Trimestral" },
  { value: MEMBERSHIP_TYPES.ANNUAL, label: "Anual" },
];

/** Catálogo de planes (producto comercial), separado de asignaciones. */
export const DEMO_MEMBERSHIP_PLANS = [
  {
    planId: "demo-plan-mensual",
    planCode: "PLAN-DEMO-M",
    name: "Acceso mensual (demo)",
    membershipType: MEMBERSHIP_TYPES.MONTHLY,
    priceIllustrativeMxn: 599,
    durationLabel: "1 mes",
    highlights: ["Acceso general demo", "Horario estándar ficticio", "Sin cobro real"],
  },
  {
    planId: "demo-plan-trimestral",
    planCode: "PLAN-DEMO-T",
    name: "Paquete trimestral (demo)",
    membershipType: MEMBERSHIP_TYPES.QUARTERLY,
    priceIllustrativeMxn: 1599,
    durationLabel: "3 meses",
    highlights: ["Precio ilustrativo por periodo", "Renovación no disponible", "Solo visualización"],
  },
  {
    planId: "demo-plan-anual",
    planCode: "PLAN-DEMO-A",
    name: "Membresía anual (demo)",
    membershipType: MEMBERSHIP_TYPES.ANNUAL,
    priceIllustrativeMxn: 5499,
    durationLabel: "12 meses",
    highlights: ["Plan ficticio premium", "Beneficios de muestra", "No genera ingresos"],
  },
];

const PLAN_BY_TYPE = Object.fromEntries(DEMO_MEMBERSHIP_PLANS.map((p) => [p.membershipType, p]));

function parseIsoUtc(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return Date.UTC(y, m - 1, d);
}

function addDaysIso(iso, days) {
  const t = parseIsoUtc(iso) + days * 86400000;
  return new Date(t).toISOString().slice(0, 10);
}

export function computeMembershipLifecycle(member, endDate, referenceDate = DEMO_REFERENCE_DATE) {
  if (member.status === MEMBER_STATUS.SUSPENDED) {
    return MEMBERSHIP_LIFECYCLE.SUSPENDED;
  }
  if (member.status === MEMBER_STATUS.EXPIRED) {
    return MEMBERSHIP_LIFECYCLE.EXPIRED;
  }
  if (endDate < referenceDate) {
    return MEMBERSHIP_LIFECYCLE.EXPIRED;
  }
  const expiringThreshold = addDaysIso(referenceDate, EXPIRING_SOON_DAYS);
  if (endDate <= expiringThreshold) {
    return MEMBERSHIP_LIFECYCLE.EXPIRING;
  }
  return MEMBERSHIP_LIFECYCLE.ACTIVE;
}

/** Una membresía asignada por socio seed (coherente con members.demo.js). */
export const DEMO_ASSIGNED_MEMBERSHIPS = DEMO_MEMBERS.map((member, index) => {
  const plan = PLAN_BY_TYPE[member.membershipType];
  const lifecycle = computeMembershipLifecycle(member, member.expiresOn);
  return {
    assignmentId: `demo-asg-${String(index + 1).padStart(3, "0")}`,
    memberId: member.memberId,
    memberCode: member.memberCode,
    fullName: member.fullName,
    planId: plan.planId,
    planCode: plan.planCode,
    planName: plan.name,
    membershipType: member.membershipType,
    startDate: member.enrolledOn,
    endDate: member.expiresOn,
    lifecycle,
    branchName: member.branchName,
    priceIllustrativeMxn: plan.priceIllustrativeMxn,
    isDemo: true,
  };
});

export const MEMBERSHIPS_PAGE_SIZE_OPTIONS = [5, 10, 25];

export function lifecycleLabel(lifecycle) {
  switch (lifecycle) {
    case MEMBERSHIP_LIFECYCLE.ACTIVE:
      return "Vigente";
    case MEMBERSHIP_LIFECYCLE.EXPIRING:
      return "Próxima a vencer";
    case MEMBERSHIP_LIFECYCLE.EXPIRED:
      return "Vencida";
    case MEMBERSHIP_LIFECYCLE.SUSPENDED:
      return "Suspendida";
    default:
      return lifecycle;
  }
}

export function lifecycleBadgeVariant(lifecycle) {
  switch (lifecycle) {
    case MEMBERSHIP_LIFECYCLE.ACTIVE:
      return "success";
    case MEMBERSHIP_LIFECYCLE.EXPIRING:
      return "warning";
    case MEMBERSHIP_LIFECYCLE.EXPIRED:
      return "neutral";
    case MEMBERSHIP_LIFECYCLE.SUSPENDED:
      return "neutral";
    default:
      return "neutral";
  }
}

export function countByLifecycle(assignments) {
  return assignments.reduce(
    (acc, row) => {
      acc[row.lifecycle] = (acc[row.lifecycle] || 0) + 1;
      return acc;
    },
    { [MEMBERSHIP_LIFECYCLE.ACTIVE]: 0, [MEMBERSHIP_LIFECYCLE.EXPIRING]: 0, [MEMBERSHIP_LIFECYCLE.EXPIRED]: 0, [MEMBERSHIP_LIFECYCLE.SUSPENDED]: 0 },
  );
}

/**
 * Catálogo único de sucursales ficticias (UI demo).
 * No usar branchId como autorización ni alcance de seguridad.
 */

export const BRANCH_STATUS = {
  ACTIVE: "activa",
  INACTIVE: "inactiva",
};

/** Valor del selector global: todas las sucursales demo. */
export const DEMO_BRANCH_ALL = "";

export const DEMO_BRANCH_CATALOG = [
  {
    branchId: "demo-branch-centro",
    branchCode: "SUC-CEN",
    name: "Centro Demo",
    locationLabel: "Av. Ficticia 100, Col. Centro Demo, CDMX (ilustrativo)",
    status: BRANCH_STATUS.ACTIVE,
    description: "Recepción principal y piso de cardio del escenario de demostración.",
  },
  {
    branchId: "demo-branch-norte",
    branchCode: "SUC-NOR",
    name: "Norte Demo",
    locationLabel: "Blvd. Norte Demo 250, Zona Industrial Ficticia (ilustrativo)",
    status: BRANCH_STATUS.ACTIVE,
    description: "Sucursal demo con área funcional y estacionamiento ficticio.",
  },
  {
    branchId: "demo-branch-sur",
    branchCode: "SUC-SUR",
    name: "Sur Demo",
    locationLabel: "Calle Sur Demo 45, Plaza Comercial Ficticia (ilustrativo)",
    status: BRANCH_STATUS.ACTIVE,
    description: "Sucursal demo orientada a clases grupales ficticias.",
  },
  {
    branchId: "demo-branch-oriente",
    branchCode: "SUC-ORI",
    name: "Oriente Demo",
    locationLabel: "Periférico Demo km 12, Ciudad Demo (ilustrativo)",
    status: BRANCH_STATUS.INACTIVE,
    description: "Sucursal inactiva de ejemplo; no recibe altas demo en socios seed.",
  },
];

/** Nombres legacy (antes arreglo plano en members.demo.js). */
export const DEMO_BRANCH_NAMES = DEMO_BRANCH_CATALOG.filter((b) => b.status === BRANCH_STATUS.ACTIVE).map(
  (b) => b.name,
);

export const BRANCH_STATUS_FILTER_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: BRANCH_STATUS.ACTIVE, label: "Activa" },
  { value: BRANCH_STATUS.INACTIVE, label: "Inactiva (demo)" },
];

export function getDemoBranchById(branchId) {
  if (!branchId) {
    return null;
  }
  return DEMO_BRANCH_CATALOG.find((b) => b.branchId === branchId) ?? null;
}

export function getDemoBranchByCode(branchCode) {
  return DEMO_BRANCH_CATALOG.find((b) => b.branchCode === branchCode) ?? null;
}

export function getDemoBranchByName(name) {
  return DEMO_BRANCH_CATALOG.find((b) => b.name === name) ?? null;
}

export function branchStatusLabel(status) {
  return status === BRANCH_STATUS.ACTIVE ? "Activa" : "Inactiva";
}

export function branchStatusBadgeVariant(status) {
  return status === BRANCH_STATUS.ACTIVE ? "success" : "neutral";
}

export function demoBranchSelectOptions() {
  return [
    { value: DEMO_BRANCH_ALL, label: "Todas las sucursales (demo)" },
    ...DEMO_BRANCH_CATALOG.filter((b) => b.status === BRANCH_STATUS.ACTIVE).map((b) => ({
      value: b.branchId,
      label: b.name,
    })),
  ];
}

export function branchFilterOptionsForLists() {
  return [
    { value: "", label: "Todas las sucursales demo" },
    ...DEMO_BRANCH_CATALOG.filter((b) => b.status === BRANCH_STATUS.ACTIVE).map((b) => ({
      value: b.branchId,
      label: b.name,
    })),
  ];
}

/** Filtro visual de interfaz; no es control de permisos. */
export function itemMatchesDemoBranch(item, selectedBranchId) {
  if (!selectedBranchId) {
    return true;
  }
  if (item.branchId) {
    return item.branchId === selectedBranchId;
  }
  const branch = getDemoBranchById(selectedBranchId);
  if (!branch) {
    return false;
  }
  return item.branchName === branch.name;
}

export function countDemoMembersByBranchId(members) {
  return members.reduce((acc, member) => {
    const key = member.branchId ?? "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

export const BRANCHES_PAGE_SIZE_OPTIONS = [4, 8, 12];

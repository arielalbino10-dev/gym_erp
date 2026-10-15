/** Socios ficticios — deterministas, no operativos. */

/** Fecha de referencia compartida con dashboard, membresías y asistencias. */
export const DEMO_REFERENCE_DATE = "2026-10-15";

export const MEMBER_STATUS = {
  ACTIVE: "activo",
  EXPIRED: "vencido",
  SUSPENDED: "suspendido",
};

export const MEMBERSHIP_TYPES = {
  MONTHLY: "mensual",
  QUARTERLY: "trimestral",
  ANNUAL: "anual",
};

export const DEMO_BRANCHES = ["Centro Demo", "Norte Demo", "Sur Demo"];

export const MEMBER_STATUS_FILTER_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: MEMBER_STATUS.ACTIVE, label: "Activo" },
  { value: MEMBER_STATUS.EXPIRED, label: "Vencido" },
  { value: MEMBER_STATUS.SUSPENDED, label: "Suspendido (demo)" },
];

export const MEMBERSHIP_FILTER_OPTIONS = [
  { value: "", label: "Todos los planes" },
  { value: MEMBERSHIP_TYPES.MONTHLY, label: "Mensual" },
  { value: MEMBERSHIP_TYPES.QUARTERLY, label: "Trimestral" },
  { value: MEMBERSHIP_TYPES.ANNUAL, label: "Anual" },
];

const MEMBERSHIP_CYCLE = [
  MEMBERSHIP_TYPES.MONTHLY,
  MEMBERSHIP_TYPES.QUARTERLY,
  MEMBERSHIP_TYPES.ANNUAL,
];

const STATUS_CYCLE = [MEMBER_STATUS.ACTIVE, MEMBER_STATUS.ACTIVE, MEMBER_STATUS.EXPIRED, MEMBER_STATUS.SUSPENDED];

function padMemberCode(index) {
  return `DEMO-M-${String(index).padStart(3, "0")}`;
}

function memberUuid(index) {
  return `d0000000-0000-4000-8000-${String(1000 + index).padStart(12, "0")}`;
}

function enrollmentIso(index) {
  const day = 1 + (index % 28);
  const month = 6 + Math.floor(index / 28);
  return `2026-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function expiryIso(index, membershipType) {
  const [y, m, d] = enrollmentIso(index).split("-").map(Number);
  const months =
    membershipType === MEMBERSHIP_TYPES.ANNUAL ? 12 : membershipType === MEMBERSHIP_TYPES.QUARTERLY ? 3 : 1;
  const end = new Date(Date.UTC(y, m - 1 + months, d));
  return end.toISOString().slice(0, 10);
}

/** Fechas alineadas al escenario demo para que estado del socio y vencimiento coincidan visualmente. */
function datesForMember(index, status) {
  if (status === MEMBER_STATUS.EXPIRED) {
    return { enrolledOn: "2026-05-15", expiresOn: "2026-09-01" };
  }
  if (status === MEMBER_STATUS.SUSPENDED) {
    return { enrolledOn: enrollmentIso(index), expiresOn: expiryIso(index, MEMBERSHIP_CYCLE[index % 3]) };
  }
  const activeVariant = index % 3;
  if (activeVariant === 0) {
    return { enrolledOn: "2026-09-01", expiresOn: "2026-11-30" };
  }
  if (activeVariant === 1) {
    return { enrolledOn: "2026-08-01", expiresOn: "2026-10-25" };
  }
  return { enrolledOn: "2026-07-01", expiresOn: "2026-12-15" };
}

export const DEMO_MEMBERS = Array.from({ length: 24 }, (_, index) => {
  const i = index + 1;
  const membershipType = MEMBERSHIP_CYCLE[index % MEMBERSHIP_CYCLE.length];
  const status = STATUS_CYCLE[index % STATUS_CYCLE.length];
  const { enrolledOn, expiresOn } = datesForMember(index, status);
  return {
    memberId: memberUuid(i),
    memberCode: padMemberCode(i),
    fullName: `Socio ficticio ${String(i).padStart(2, "0")}`,
    phone: `55 8000 ${String(2000 + i).slice(-4)}`,
    membershipType,
    status,
    enrolledOn,
    expiresOn,
    branchName: DEMO_BRANCHES[index % DEMO_BRANCHES.length],
    isDemo: true,
  };
});

export const MEMBERS_PAGE_SIZE_OPTIONS = [5, 10, 25];

function addMonthsToIso(isoDate, months) {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1 + months, d)).toISOString().slice(0, 10);
}

export function createSessionDemoMember(fields, sessionIndex) {
  const membershipType = fields.membershipType || MEMBERSHIP_TYPES.MONTHLY;
  const enrolledOn = "2026-10-15";
  const months =
    membershipType === MEMBERSHIP_TYPES.ANNUAL
      ? 12
      : membershipType === MEMBERSHIP_TYPES.QUARTERLY
        ? 3
        : 1;
  return {
    memberId: `d0000000-0000-4000-8999-${String(9000 + sessionIndex).padStart(12, "0")}`,
    memberCode: `DEMO-M-S${String(sessionIndex).padStart(2, "0")}`,
    fullName: fields.fullName.trim(),
    phone: fields.phone.trim(),
    membershipType,
    status: MEMBER_STATUS.ACTIVE,
    enrolledOn,
    expiresOn: addMonthsToIso(enrolledOn, months),
    branchName: fields.branchName || DEMO_BRANCHES[0],
    isDemo: true,
    sessionOnly: true,
  };
}

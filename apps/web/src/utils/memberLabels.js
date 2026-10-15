import { MEMBER_STATUS, MEMBERSHIP_TYPES } from "../demo/members.demo.js";

export function membershipTypeLabel(type) {
  switch (type) {
    case MEMBERSHIP_TYPES.MONTHLY:
      return "Mensual";
    case MEMBERSHIP_TYPES.QUARTERLY:
      return "Trimestral";
    case MEMBERSHIP_TYPES.ANNUAL:
      return "Anual";
    default:
      return type;
  }
}

export function memberStatusLabel(status) {
  switch (status) {
    case MEMBER_STATUS.ACTIVE:
      return "Activo";
    case MEMBER_STATUS.EXPIRED:
      return "Vencido";
    case MEMBER_STATUS.SUSPENDED:
      return "Suspendido";
    default:
      return status;
  }
}

export function memberStatusBadgeVariant(status) {
  switch (status) {
    case MEMBER_STATUS.ACTIVE:
      return "success";
    case MEMBER_STATUS.EXPIRED:
      return "warning";
    case MEMBER_STATUS.SUSPENDED:
      return "neutral";
    default:
      return "neutral";
  }
}

export function formatDemoDate(iso) {
  if (!iso) {
    return "—";
  }
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(y, m - 1, d)));
}

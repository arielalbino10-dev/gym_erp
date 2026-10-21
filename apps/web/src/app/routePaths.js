/** Rutas públicas y operativas (referencia para navegación y tests). */
export const ROUTE_PATHS = {
  landing: "/",
  login: "/login",
  tenantSelect: "/seleccionar-gimnasio",
  branches: "/sucursales",
  members: "/socios",
  memberships: "/membresias",
  attendance: "/asistencias",
  settings: "/configuracion",
  dashboard: "/dashboard",
};

export const LANDING_SECTION_IDS = {
  features: "funcionalidades",
  benefits: "beneficios",
  productPreview: "vista-producto",
  plans: "planes",
  howItWorks: "como-funciona",
  about: "nosotros",
  faq: "faq",
};

export function landingSectionHash(sectionId) {
  return `#${sectionId}`;
}

/** Prefijos que requieren sesión gym (alineado con routes.jsx). */
export const GYM_AUTH_ROUTE_PREFIXES = [
  ROUTE_PATHS.tenantSelect,
  ROUTE_PATHS.branches,
  ROUTE_PATHS.members,
  ROUTE_PATHS.memberships,
  ROUTE_PATHS.attendance,
  ROUTE_PATHS.settings,
  ROUTE_PATHS.dashboard,
];

export function isGymAuthenticatedPath(pathname) {
  if (!pathname || pathname === ROUTE_PATHS.landing || pathname === ROUTE_PATHS.login) {
    return false;
  }
  return GYM_AUTH_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

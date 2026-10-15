/** Rutas principales del ERP (UI-01.2). */

export const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/socios", label: "Socios" },
  { to: "/membresias", label: "Membresías" },
  { to: "/asistencias", label: "Asistencias" },
  { to: "/sucursales", label: "Sucursales" },
  { to: "/configuracion", label: "Configuración" },
];

function pathMatchesNavItem(pathname, to) {
  if (to === "/") {
    return pathname === "/";
  }
  return pathname === to || pathname.startsWith(`${to}/`);
}

export function titleForPathname(pathname) {
  const match = NAV_ITEMS.find((item) => pathMatchesNavItem(pathname, item.to));
  if (match) {
    return match.label;
  }
  return "Página no encontrada";
}

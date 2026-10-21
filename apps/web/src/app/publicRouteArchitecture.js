import { ROUTE_PATHS } from "./routePaths.js";

/** Rutas de marketing que no montan GymAuthProvider ni consultan sesión gym. */
export const PUBLIC_MARKETING_PATHS = Object.freeze([ROUTE_PATHS.landing]);

export function isPublicMarketingPath(pathname) {
  if (!pathname) {
    return false;
  }
  const normalized = pathname.endsWith("/") && pathname.length > 1 ? pathname.slice(0, -1) : pathname;
  return PUBLIC_MARKETING_PATHS.includes(normalized);
}

export function shouldBootstrapGymAuth(pathname) {
  return !isPublicMarketingPath(pathname);
}

/**
 * El ERP operativo no debe registrar index en "/" bajo layouts pathless:
 * competiría con la landing pública (RequireGymAuth → /login).
 */
export const OPERATIONAL_APP_INDEX_PATH = null;

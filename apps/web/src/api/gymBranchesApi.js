import { gymFetch } from "./gymHttpClient.js";

/** @typedef {{ branch_id: string, name: string, status: string, timezone: string, code?: string | null }} ApiBranch */

export async function listGymBranches(options = {}) {
  const result = await gymFetch("/gym/branches/", { signal: options.signal });
  return result.data?.branches ?? [];
}

export async function getGymBranch(branchId) {
  const result = await gymFetch(`/gym/branches/${encodeURIComponent(branchId)}`);
  return result.data;
}

export async function createGymBranch({ name, timezone, code }, options = {}) {
  const payload = { name };
  if (timezone) {
    payload.timezone = timezone;
  }
  if (code) {
    payload.code = code;
  }
  const result = await gymFetch("/gym/branches/", {
    method: "POST",
    body: JSON.stringify(payload),
    signal: options.signal,
  });
  return result.data;
}

/** Adapta respuesta API al shape usado por la UI de sucursales. */
export function mapApiBranchToUi(apiBranch) {
  return {
    branchId: apiBranch.branch_id,
    name: apiBranch.name,
    branchCode: apiBranch.code || "—",
    status: apiBranch.status === "active" ? "activa" : apiBranch.status,
    timezone: apiBranch.timezone,
    locationLabel: apiBranch.timezone,
    description: "",
  };
}

export function canCreateBranchesFromSession(session) {
  if (!session?.gym_roles?.length) {
    return false;
  }
  return session.gym_roles.some((role) => role === "gym_owner" || role === "gym_admin");
}

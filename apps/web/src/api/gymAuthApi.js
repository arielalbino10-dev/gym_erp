import { gymFetch } from "./gymHttpClient.js";

export async function gymLogin({ email, password }) {
  return gymFetch("/gym/auth/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ email, password }),
  });
}

export async function gymLogout() {
  return gymFetch("/gym/auth/logout", { method: "POST" });
}

export async function fetchGymSession() {
  const result = await gymFetch("/gym/auth/session");
  return result.data;
}

export async function fetchGymMemberships() {
  const result = await gymFetch("/gym/auth/memberships");
  return result.data?.memberships ?? [];
}

export async function selectGymTenant(tenantId) {
  return gymFetch("/gym/auth/select-tenant", {
    method: "POST",
    body: JSON.stringify({ tenant_id: tenantId }),
  });
}

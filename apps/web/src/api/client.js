const DEFAULT_BASE = "/api/v1";

function apiBaseUrl() {
  const fromEnv = import.meta.env.VITE_API_BASE_URL;
  if (fromEnv && String(fromEnv).trim()) {
    return String(fromEnv).replace(/\/$/, "");
  }
  return DEFAULT_BASE;
}

/**
 * @returns {Promise<{ ok: boolean, status: number, body: object | null }>}
 */
export async function fetchHealthReady() {
  const url = `${apiBaseUrl()}/health/ready`;
  const response = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "omit",
  });

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  return {
    ok: response.ok,
    status: response.status,
    body,
  };
}

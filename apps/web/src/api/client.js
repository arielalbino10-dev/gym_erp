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
const DEFAULT_HEALTH_TIMEOUT_MS = 8000;

export async function fetchHealthReady({ timeoutMs = DEFAULT_HEALTH_TIMEOUT_MS } = {}) {
  const url = `${apiBaseUrl()}/health/ready`;
  const signal =
    typeof AbortSignal !== "undefined" && AbortSignal.timeout
      ? AbortSignal.timeout(timeoutMs)
      : undefined;

  const response = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "omit",
    signal,
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

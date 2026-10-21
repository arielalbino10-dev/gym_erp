/** Cliente HTTP gym: cookies HttpOnly + CSRF en memoria (H3-C.1 / H3-C.1.1). */

const CSRF_HEADER = "X-CSRF-Token";
const MUTATION_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** @typedef {"session" | "csrf" | "permission" | "not_found" | "conflict" | "unavailable" | "generic"} GymApiErrorKind */

let csrfTokenMemory = null;
/** @type {(() => void | Promise<void>) | null} */
let sessionExpiredHandler = null;
/** @type {(() => void | Promise<void>) | null} */
let csrfRecoveryHandler = null;

export function apiBaseUrl() {
  const fromEnv =
    typeof import.meta !== "undefined" ? import.meta.env?.VITE_API_BASE_URL : undefined;
  if (fromEnv && String(fromEnv).trim()) {
    return String(fromEnv).replace(/\/$/, "");
  }
  return "/api/v1";
}

export function getBrowserOrigin() {
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin;
  }
  return "http://127.0.0.1:5173";
}

export function setCsrfToken(token) {
  csrfTokenMemory = token && String(token).trim() ? String(token).trim() : null;
}

export function getCsrfToken() {
  return csrfTokenMemory;
}

export function captureCsrfFromResponse(response) {
  const header = response.headers.get(CSRF_HEADER);
  if (header && header.trim()) {
    setCsrfToken(header.trim());
  }
}

/** @param {(() => void | Promise<void>) | null} handler */
export function setGymSessionExpiredHandler(handler) {
  sessionExpiredHandler = handler;
}

/** @param {(() => void | Promise<void>) | null} handler */
export function setGymCsrfRecoveryHandler(handler) {
  csrfRecoveryHandler = handler;
}

export class GymApiError extends Error {
  /**
   * @param {string} message
   * @param {{ status?: number, code?: string, detail?: unknown, kind?: GymApiErrorKind }} [meta]
   */
  constructor(message, { status, code, detail, kind } = {}) {
    super(message);
    this.name = "GymApiError";
    this.status = status ?? 0;
    this.code = code;
    this.detail = detail ?? message;
    this.kind = kind ?? "generic";
  }
}

async function parseJsonBody(response) {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/**
 * @param {number} status
 * @param {Record<string, unknown> | null} body
 * @returns {GymApiErrorKind}
 */
export function classifyHttpErrorKind(status, body) {
  if (status === 401) {
    return "session";
  }
  if (status === 403) {
    if (body?.code === "csrf_invalid") {
      return "csrf";
    }
    if (body?.code === "tenant_not_selected") {
      return "permission";
    }
    return "permission";
  }
  if (status === 404) {
    return "not_found";
  }
  if (status === 409) {
    return "conflict";
  }
  if (status === 503) {
    return "unavailable";
  }
  return "generic";
}

function messageForStatus(status, body) {
  const detail = body?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (status === 401) {
    return "Sesión no válida o expirada.";
  }
  if (status === 403) {
    return "Acceso no permitido.";
  }
  if (status === 404) {
    return "Recurso no encontrado.";
  }
  if (status === 409) {
    return "Conflicto al procesar la solicitud.";
  }
  if (status === 503) {
    return "Servicio temporalmente no disponible.";
  }
  return "Error al comunicarse con el servidor.";
}

async function invokeSessionExpired() {
  if (sessionExpiredHandler) {
    await sessionExpiredHandler();
  }
}

async function performFetch(url, method, headers, body, signal) {
  return fetch(url, {
    method,
    credentials: "include",
    headers,
    body,
    signal,
  });
}

/**
 * @param {string} path - Ruta relativa bajo /api/v1 (p. ej. /gym/auth/session)
 * @param {RequestInit & { auth?: boolean, _csrfRetried?: boolean }} [options]
 */
export async function gymFetch(path, options = {}) {
  const authAware = options.auth !== false;
  const method = (options.method || "GET").toUpperCase();
  const url = `${apiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = {
    Accept: "application/json",
    ...(options.headers || {}),
  };
  if (MUTATION_METHODS.has(method)) {
    if (csrfTokenMemory) {
      headers[CSRF_HEADER] = csrfTokenMemory;
    }
    if (options.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
  }

  const response = await performFetch(url, method, headers, options.body, options.signal);

  captureCsrfFromResponse(response);

  if (response.status === 204) {
    return { ok: true, status: 204, data: null };
  }

  const body = await parseJsonBody(response);
  if (!response.ok) {
    const kind = classifyHttpErrorKind(response.status, body);
    if (authAware && response.status === 401) {
      await invokeSessionExpired();
    }
    const csrfKind = response.status === 403 && classifyHttpErrorKind(403, body) === "csrf";
    if (
      authAware &&
      csrfKind &&
      MUTATION_METHODS.has(method) &&
      !options._csrfRetried &&
      csrfRecoveryHandler
    ) {
      await csrfRecoveryHandler();
      return gymFetch(path, { ...options, _csrfRetried: true });
    }
    throw new GymApiError(messageForStatus(response.status, body), {
      status: response.status,
      code: body?.code,
      detail: body?.detail,
      kind,
    });
  }

  return { ok: true, status: response.status, data: body };
}

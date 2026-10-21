import assert from "node:assert/strict";
import { afterEach, beforeEach, describe, it, mock } from "node:test";
import {
  GymApiError,
  classifyHttpErrorKind,
  gymFetch,
  setCsrfToken,
  setGymCsrfRecoveryHandler,
  setGymSessionExpiredHandler,
} from "./gymHttpClient.js";

describe("classifyHttpErrorKind", () => {
  it("distinguishes session, permission, csrf and unavailable", () => {
    assert.equal(classifyHttpErrorKind(401, null), "session");
    assert.equal(classifyHttpErrorKind(403, { code: "csrf_invalid" }), "csrf");
    assert.equal(classifyHttpErrorKind(403, { code: "tenant_not_selected" }), "permission");
    assert.equal(classifyHttpErrorKind(503, null), "unavailable");
  });
});

describe("gymFetch HTTP policy", () => {
  /** @type {import("node:test").Mock<(input: RequestInfo, init?: RequestInit) => Promise<Response>>} */
  let fetchMock;

  beforeEach(() => {
    setCsrfToken(null);
    setGymSessionExpiredHandler(null);
    setGymCsrfRecoveryHandler(null);
    fetchMock = mock.fn();
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    mock.restoreAll();
  });

  function jsonResponse(status, body, headers = {}) {
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json", ...headers },
    });
  }

  it("401 clears session via handler and does not retry", async () => {
    let cleared = 0;
    setGymSessionExpiredHandler(() => {
      cleared += 1;
    });
    fetchMock.mock.mockImplementation(async () => jsonResponse(401, { detail: "No autenticado." }));

    await assert.rejects(
      () => gymFetch("/gym/branches/"),
      (err) => err instanceof GymApiError && err.kind === "session",
    );
    assert.equal(cleared, 1);
    assert.equal(fetchMock.mock.callCount(), 1);
  });

  it("403 permission does not invoke session handler", async () => {
    let cleared = 0;
    setGymSessionExpiredHandler(() => {
      cleared += 1;
    });
    fetchMock.mock.mockImplementation(async () =>
      jsonResponse(403, { detail: "Acceso no permitido." }),
    );

    await assert.rejects(
      () =>
        gymFetch("/gym/branches/", {
          method: "POST",
          body: "{}",
        }),
      (err) => err instanceof GymApiError && err.kind === "permission",
    );
    assert.equal(cleared, 0);
    assert.equal(fetchMock.mock.callCount(), 1);
  });

  it("403 csrf retries once after recovery handler", async () => {
    let recoveries = 0;
    setGymCsrfRecoveryHandler(async () => {
      recoveries += 1;
      setCsrfToken("fresh-token");
    });
    fetchMock.mock.mockImplementation(async () =>
      jsonResponse(403, { detail: "Solicitud no permitida.", code: "csrf_invalid" }),
    );

    await assert.rejects(() => gymFetch("/gym/branches/", { method: "POST", body: "{}" }));
    assert.equal(recoveries, 1);
    assert.equal(fetchMock.mock.callCount(), 2);
  });

  it("login 401 does not trigger global session handler", async () => {
    let cleared = 0;
    setGymSessionExpiredHandler(() => {
      cleared += 1;
    });
    fetchMock.mock.mockImplementation(async () =>
      jsonResponse(401, { detail: "Credenciales inválidas o solicitud no autorizada." }),
    );

    await assert.rejects(() =>
      gymFetch("/gym/auth/login", {
        method: "POST",
        auth: false,
        body: "{}",
      }),
    );
    assert.equal(cleared, 0);
  });
});

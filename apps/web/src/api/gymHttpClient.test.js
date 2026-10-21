import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  GymApiError,
  captureCsrfFromResponse,
  getCsrfToken,
  setCsrfToken,
} from "./gymHttpClient.js";

describe("gymHttpClient CSRF memory", () => {
  it("stores and clears token in memory only", () => {
    setCsrfToken("abc");
    assert.equal(getCsrfToken(), "abc");
    setCsrfToken(null);
    assert.equal(getCsrfToken(), null);
  });

  it("reads X-CSRF-Token from response headers", () => {
    setCsrfToken(null);
    const response = {
      headers: {
        get(name) {
          return name === "X-CSRF-Token" ? " token-from-server " : null;
        },
      },
    };
    captureCsrfFromResponse(response);
    assert.equal(getCsrfToken(), "token-from-server");
  });
});

describe("GymApiError", () => {
  it("carries HTTP status", () => {
    const err = new GymApiError("x", { status: 403 });
    assert.equal(err.status, 403);
  });
});

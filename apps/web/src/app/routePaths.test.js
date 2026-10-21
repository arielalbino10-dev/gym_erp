import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  GYM_AUTH_ROUTE_PREFIXES,
  isGymAuthenticatedPath,
  LANDING_SECTION_IDS,
  landingSectionHash,
  ROUTE_PATHS,
} from "./routePaths.js";

describe("routePaths", () => {
  it("exposes public landing and gym login paths", () => {
    assert.equal(ROUTE_PATHS.landing, "/");
    assert.equal(ROUTE_PATHS.login, "/login");
  });

  it("builds in-page section hashes for landing CTAs", () => {
    assert.equal(landingSectionHash(LANDING_SECTION_IDS.benefits), "#beneficios");
    assert.equal(landingSectionHash(LANDING_SECTION_IDS.plans), "#planes");
  });

  it("treats operational gym routes as authenticated paths", () => {
    assert.equal(isGymAuthenticatedPath("/sucursales"), true);
    assert.equal(isGymAuthenticatedPath("/seleccionar-gimnasio"), true);
    assert.equal(isGymAuthenticatedPath("/"), false);
    assert.equal(isGymAuthenticatedPath("/login"), false);
  });

  it("keeps tenant selection and branches under protected prefixes", () => {
    assert.ok(GYM_AUTH_ROUTE_PREFIXES.includes(ROUTE_PATHS.tenantSelect));
    assert.ok(GYM_AUTH_ROUTE_PREFIXES.includes(ROUTE_PATHS.branches));
  });
});

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { ROUTE_PATHS } from "./routePaths.js";
import {
  isPublicMarketingPath,
  OPERATIONAL_APP_INDEX_PATH,
  shouldBootstrapGymAuth,
} from "./publicRouteArchitecture.js";

describe("publicRouteArchitecture", () => {
  it("treats landing as public marketing without gym auth bootstrap", () => {
    assert.equal(isPublicMarketingPath("/"), true);
    assert.equal(shouldBootstrapGymAuth("/"), false);
  });

  it("requires gym auth bootstrap on login and operational routes", () => {
    assert.equal(shouldBootstrapGymAuth(ROUTE_PATHS.login), true);
    assert.equal(shouldBootstrapGymAuth(ROUTE_PATHS.branches), true);
    assert.equal(shouldBootstrapGymAuth(ROUTE_PATHS.tenantSelect), true);
  });

  it("does not map operational shell index to landing path", () => {
    assert.notEqual(OPERATIONAL_APP_INDEX_PATH, ROUTE_PATHS.landing);
  });
});

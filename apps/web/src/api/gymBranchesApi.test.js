import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { canCreateBranchesFromSession, mapApiBranchToUi } from "./gymBranchesApi.js";

describe("gymBranchesApi", () => {
  it("maps API branch to UI shape", () => {
    const ui = mapApiBranchToUi({
      branch_id: "550e8400-e29b-41d4-a716-446655440099",
      name: "Centro",
      status: "active",
      timezone: "America/Mexico_City",
      code: "CEN",
    });
    assert.equal(ui.branchId, "550e8400-e29b-41d4-a716-446655440099");
    assert.equal(ui.status, "activa");
    assert.equal(ui.branchCode, "CEN");
  });

  it("derives create capability from server roles", () => {
    assert.equal(canCreateBranchesFromSession({ gym_roles: ["gym_owner"] }), true);
    assert.equal(canCreateBranchesFromSession({ gym_roles: ["branch_admin"] }), false);
    assert.equal(canCreateBranchesFromSession(null), false);
  });
});

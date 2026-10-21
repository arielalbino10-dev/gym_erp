import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { WHATSAPP_COMMERCIAL } from "./commercialContact.js";
import {
  CONTRACT_STEPS,
  LANDING_FAQ,
  LANDING_FEATURES,
  PLANS_PLACEHOLDER_MESSAGE,
  PLANS_SKELETON_TIERS,
} from "./landingContent.js";

describe("landingContent", () => {
  it("does not publish invented monthly or annual prices", () => {
    const serialized = JSON.stringify({
      tiers: PLANS_SKELETON_TIERS,
      message: PLANS_PLACEHOLDER_MESSAGE,
      features: LANDING_FEATURES,
    }).toLowerCase();
    assert.equal(/\$\d/.test(serialized), false);
    assert.equal(/\/mes|usd|mxn|eur/.test(serialized), false);
  });

  it("marks demo and planned modules explicitly", () => {
    const branches = LANDING_FEATURES.find((f) => f.id === "branches");
    const members = LANDING_FEATURES.find((f) => f.id === "members");
    const reports = LANDING_FEATURES.find((f) => f.id === "reports");
    assert.equal(branches?.availability, "available");
    assert.equal(members?.availability, "demo");
    assert.equal(reports?.availability, "planned");
  });

  it("documents commercial pending state for plans", () => {
    assert.match(PLANS_PLACEHOLDER_MESSAGE, /preparación|definiendo/i);
    assert.ok(PLANS_SKELETON_TIERS.every((tier) => tier.name && tier.blurb));
  });

  it("includes WhatsApp in FAQ aligned with contact config", () => {
    const withNumber = LANDING_FAQ.find((item) =>
      item.answer.includes(WHATSAPP_COMMERCIAL.displayNumber),
    );
    assert.ok(withNumber);
    const waQuestion = LANDING_FAQ.find((item) => /whatsapp/i.test(item.question));
    assert.ok(waQuestion);
  });

  it("defines contract timeline steps as structured items", () => {
    assert.equal(CONTRACT_STEPS.length, 7);
    assert.ok(CONTRACT_STEPS.every((step) => step.title && step.detail));
  });
});

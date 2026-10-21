import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  buildWhatsAppUrl,
  WHATSAPP_COMMERCIAL,
  WHATSAPP_MESSAGE_TEMPLATES,
} from "./commercialContact.js";

describe("commercialContact", () => {
  it("uses the authorized international WhatsApp number", () => {
    assert.equal(WHATSAPP_COMMERCIAL.waMeNumber, "522211803440");
    assert.equal(WHATSAPP_COMMERCIAL.baseUrl, "https://wa.me/522211803440");
    assert.match(WHATSAPP_COMMERCIAL.displayNumber, /221 180 3440/);
  });

  it("builds wa.me URLs with encoded default message", () => {
    const url = buildWhatsAppUrl("general");
    assert.ok(url.startsWith("https://wa.me/522211803440?text="));
    const encoded = url.split("?text=")[1];
    assert.equal(decodeURIComponent(encoded), WHATSAPP_MESSAGE_TEMPLATES.general);
  });

  it("builds plans-specific message URL", () => {
    const url = buildWhatsAppUrl("plans");
    const encoded = url.split("?text=")[1];
    assert.match(decodeURIComponent(encoded), /planes mensuales y anuales/i);
  });

  it("rejects unknown message keys", () => {
    assert.throws(() => buildWhatsAppUrl("arbitrary-injection"), /no permitida/i);
  });
});

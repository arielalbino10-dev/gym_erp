/** Contacto comercial centralizado (landing pública). */

export const WHATSAPP_COMMERCIAL = Object.freeze({
  displayNumber: "+52 1 221 180 3440",
  waMeNumber: "522211803440",
  baseUrl: "https://wa.me/522211803440",
});

export const WHATSAPP_MESSAGE_TEMPLATES = Object.freeze({
  general:
    "Hola, buen día. Me interesa conocer más sobre Gym ERP y los planes disponibles para administrar mi gimnasio.",
  plans:
    "Hola, buen día. Quisiera recibir información sobre los planes mensuales y anuales de Gym ERP para mi gimnasio.",
});

const ALLOWED_MESSAGE_KEYS = new Set(Object.keys(WHATSAPP_MESSAGE_TEMPLATES));

/**
 * @param {'general' | 'plans'} messageKey
 * @returns {string}
 */
export function buildWhatsAppUrl(messageKey = "general") {
  if (!ALLOWED_MESSAGE_KEYS.has(messageKey)) {
    throw new Error("Clave de mensaje WhatsApp no permitida.");
  }
  const text = WHATSAPP_MESSAGE_TEMPLATES[messageKey];
  return `${WHATSAPP_COMMERCIAL.baseUrl}?text=${encodeURIComponent(text)}`;
}

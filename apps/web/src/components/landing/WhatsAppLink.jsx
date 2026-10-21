import { buildWhatsAppUrl } from "../../landing/commercialContact.js";
import WhatsAppIcon from "./WhatsAppIcon.jsx";

export default function WhatsAppLink({
  messageKey = "general",
  className = "",
  showIcon = false,
  children,
  ariaLabel,
}) {
  const href = buildWhatsAppUrl(messageKey);
  const label =
    ariaLabel ||
    (messageKey === "plans"
      ? "Consultar planes por WhatsApp (abre en una pestaña nueva)"
      : "Contactar por WhatsApp (abre en una pestaña nueva)");

  return (
    <a
      className={className}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
    >
      {showIcon ? <WhatsAppIcon className="landing-wa-link__icon" /> : null}
      {children}
    </a>
  );
}

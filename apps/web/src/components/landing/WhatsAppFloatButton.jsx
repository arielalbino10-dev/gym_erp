import WhatsAppLink from "./WhatsAppLink.jsx";

export default function WhatsAppFloatButton() {
  return (
    <WhatsAppLink
      messageKey="general"
      className="landing-wa-float"
      showIcon
      ariaLabel="Contactar a Gym ERP por WhatsApp"
    >
      <span className="landing-wa-float__label">WhatsApp</span>
    </WhatsAppLink>
  );
}

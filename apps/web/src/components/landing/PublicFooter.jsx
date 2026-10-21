import { Link } from "react-router-dom";
import { landingSectionHash, LANDING_SECTION_IDS, ROUTE_PATHS } from "../../app/routePaths.js";
import { WHATSAPP_COMMERCIAL } from "../../landing/commercialContact.js";
import { LANDING_NAV } from "../../landing/landingContent.js";
import WhatsAppLink from "./WhatsAppLink.jsx";

export default function PublicFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="landing-footer">
      <div className="landing-footer__grid">
        <div>
          <p className="landing-footer__brand">Gym ERP</p>
          <p className="landing-footer__tagline">
            Software de gestión para gimnasios: sucursales, permisos y operación centralizada.
          </p>
        </div>
        <nav aria-label="Secciones del sitio">
          <p className="landing-footer__heading">Explorar</p>
          <ul className="landing-footer__links">
            {LANDING_NAV.map((item) => (
              <li key={item.sectionId}>
                <a href={landingSectionHash(item.sectionId)}>{item.label}</a>
              </li>
            ))}
            <li>
              <a href={landingSectionHash(LANDING_SECTION_IDS.about)}>Quiénes somos</a>
            </li>
            <li>
              <a href={landingSectionHash(LANDING_SECTION_IDS.faq)}>Preguntas frecuentes</a>
            </li>
          </ul>
        </nav>
        <div>
          <p className="landing-footer__heading">Acceso y contacto</p>
          <ul className="landing-footer__links">
            <li>
              <Link to={ROUTE_PATHS.login}>Iniciar sesión (gimnasio)</Link>
            </li>
            <li>
              <WhatsAppLink messageKey="general">
                WhatsApp: {WHATSAPP_COMMERCIAL.displayNumber}
              </WhatsAppLink>
            </li>
          </ul>
          <p className="landing-footer__pending">
            Aviso de privacidad, términos y redes sociales: enlaces disponibles cuando se publiquen
            los documentos.
          </p>
        </div>
      </div>
      <p className="landing-footer__copy">© {year} Gym ERP. Todos los derechos reservados.</p>
    </footer>
  );
}

import { useEffect } from "react";
import { Link } from "react-router-dom";
import { landingSectionHash, LANDING_SECTION_IDS, ROUTE_PATHS } from "../app/routePaths.js";
import LandingFaq from "../components/landing/LandingFaq.jsx";
import LandingIcon from "../components/landing/LandingIcon.jsx";
import LandingTimeline from "../components/landing/LandingTimeline.jsx";
import ProductPreviewHero from "../components/landing/ProductPreviewHero.jsx";
import ProductPreviewShowcase from "../components/landing/ProductPreviewShowcase.jsx";
import PublicFooter from "../components/landing/PublicFooter.jsx";
import PublicHeader from "../components/landing/PublicHeader.jsx";
import WhatsAppFloatButton from "../components/landing/WhatsAppFloatButton.jsx";
import WhatsAppLink from "../components/landing/WhatsAppLink.jsx";
import SkipLink from "../components/layout/SkipLink.jsx";
import Badge from "../components/ui/Badge.jsx";
import {
  AVAILABILITY_LABELS,
  LANDING_BENEFITS,
  LANDING_FEATURES,
  PLANS_PLACEHOLDER_DETAIL,
  PLANS_PLACEHOLDER_MESSAGE,
  PLANS_SKELETON_TIERS,
} from "../landing/landingContent.js";

function availabilityBadgeVariant(availability) {
  if (availability === "available") {
    return "success";
  }
  if (availability === "demo") {
    return "demo";
  }
  return "neutral";
}

export default function LandingPage() {
  useEffect(() => {
    document.title = "Gym ERP — Gestión para gimnasios";
    return () => {
      document.title = "Gym ERP";
    };
  }, []);

  return (
    <div className="landing">
      <SkipLink />
      <PublicHeader />
      <main id="main-content">
        <section className="landing-hero" aria-labelledby="landing-hero-title">
          <div className="landing-hero__backdrop" aria-hidden="true" />
          <div className="landing-hero__grid">
            <div className="landing-hero__content">
              <p className="landing-hero__eyebrow">Plataforma SaaS para gimnasios</p>
              <h1 id="landing-hero-title" className="landing-hero__title">
                Tu gimnasio, bajo control.
              </h1>
              <p className="landing-hero__subtitle">
                Organiza tus sucursales y administra tu operación desde una plataforma diseñada
                para acompañar el crecimiento de tu gimnasio.
              </p>
              <div className="landing-hero__actions">
                <a
                  className="landing-cta landing-cta--primary"
                  href={landingSectionHash(LANDING_SECTION_IDS.benefits)}
                >
                  Explorar beneficios
                </a>
                <a
                  className="landing-cta landing-cta--secondary"
                  href={landingSectionHash(LANDING_SECTION_IDS.plans)}
                >
                  Ver planes
                </a>
                <Link className="landing-cta landing-cta--ghost" to={ROUTE_PATHS.login}>
                  Iniciar sesión
                </Link>
              </div>
              <p className="landing-hero__contact">
                ¿Prefiere hablar con alguien?{" "}
                <WhatsAppLink messageKey="general" className="landing-hero__wa">
                  Escríbanos por WhatsApp
                </WhatsAppLink>
              </p>
            </div>
            <div className="landing-hero__visual">
              <ProductPreviewHero />
              <p className="landing-hero__visual-caption">Vista demostrativa — no datos reales</p>
            </div>
          </div>
        </section>

        <section
          className="landing-section"
          id={LANDING_SECTION_IDS.benefits}
          aria-labelledby="landing-benefits-title"
        >
          <div className="landing-section__inner">
            <div className="landing-section__intro">
              <h2 id="landing-benefits-title" className="landing-section__title">
                Beneficios
              </h2>
              <p className="landing-section__lead">
                Menos dispersión administrativa, más claridad para su equipo y una base tecnológica
                pensada para el día a día del fitness.
              </p>
            </div>
            <ul className="landing-bento">
              {LANDING_BENEFITS.map((item) => (
                <li
                  key={item.id}
                  className={`landing-bento__item landing-bento__item--${item.size}`}
                >
                  <LandingIcon name={item.icon} className="landing-bento__icon" />
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section
          className="landing-section landing-section--alt"
          id={LANDING_SECTION_IDS.features}
          aria-labelledby="landing-features-title"
        >
          <div className="landing-section__inner">
            <h2 id="landing-features-title" className="landing-section__title">
              Funcionalidades
            </h2>
            <p className="landing-section__lead">
              Cada módulo indica si está operativo hoy, disponible solo como demostración visual o
              planificado en la hoja de ruta.
            </p>
            <ul className="landing-features-grid">
              {LANDING_FEATURES.map((feature) => (
                <li key={feature.id} className="landing-feature-card">
                  <div className="landing-feature-card__head">
                    <h3>{feature.title}</h3>
                    <Badge variant={availabilityBadgeVariant(feature.availability)}>
                      {AVAILABILITY_LABELS[feature.availability]}
                    </Badge>
                  </div>
                  <p>{feature.description}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section
          className="landing-section landing-section--dark"
          id={LANDING_SECTION_IDS.productPreview}
          aria-labelledby="landing-preview-title"
        >
          <div className="landing-section__inner landing-section__inner--split">
            <div className="landing-section__copy">
              <h2 id="landing-preview-title" className="landing-section__title landing-section__title--on-dark">
                Vista previa del producto
              </h2>
              <p className="landing-section__lead landing-section__lead--on-dark">
                El módulo de sucursales combina tabla operativa, estados visibles y navegación
                alineada con el ERP autenticado — aquí en una composición ampliada para explorar el
                detalle.
              </p>
            </div>
            <ProductPreviewShowcase />
          </div>
        </section>

        <section
          className="landing-section landing-section--alt"
          id={LANDING_SECTION_IDS.plans}
          aria-labelledby="landing-plans-title"
        >
          <div className="landing-section__inner">
            <h2 id="landing-plans-title" className="landing-section__title">
              Planes SaaS
            </h2>
            <p className="landing-plans-status" role="status">
              {PLANS_PLACEHOLDER_MESSAGE}
            </p>
            <p className="landing-section__lead">{PLANS_PLACEHOLDER_DETAIL}</p>
            <ul className="landing-plans-skeleton" aria-label="Referencias de planes futuros">
              {PLANS_SKELETON_TIERS.map((tier) => (
                <li key={tier.name} className="landing-plan-card">
                  <h3>{tier.name}</h3>
                  <p className="landing-plan-card__price">Tarifa por confirmar</p>
                  <p className="landing-plan-card__note">{tier.blurb}</p>
                  <ul className="landing-plan-card__limits">
                    <li>Límites y beneficios: pendientes de catálogo</li>
                    <li>Mensual / anual: se publicará con el catálogo</li>
                  </ul>
                </li>
              ))}
            </ul>
            <div className="landing-plans-cta">
              <WhatsAppLink messageKey="plans" className="landing-cta landing-cta--whatsapp">
                Consultar planes por WhatsApp
              </WhatsAppLink>
              <p className="landing-plans-cta__hint">
                Canal comercial activo mientras preparamos el formulario de solicitud en el sitio.
              </p>
            </div>
          </div>
        </section>

        <section
          className="landing-section"
          id={LANDING_SECTION_IDS.howItWorks}
          aria-labelledby="landing-how-title"
        >
          <div className="landing-section__inner">
            <h2 id="landing-how-title" className="landing-section__title">
              Cómo funcionará la contratación
            </h2>
            <p className="landing-section__lead">
              Proceso con revisión manual en cada etapa. Mientras tanto, puede solicitar información
              por WhatsApp; el formulario web llegará en una fase posterior.
            </p>
            <LandingTimeline />
          </div>
        </section>

        <section
          className="landing-section landing-section--alt landing-about-section"
          id={LANDING_SECTION_IDS.about}
          aria-labelledby="landing-about-title"
        >
          <div className="landing-section__inner landing-about">
            <div className="landing-about__panel">
              <h2 id="landing-about-title" className="landing-section__title">
                Quiénes somos
              </h2>
              <p className="landing-about__lead">
                Gym ERP es una plataforma orientada a facilitar la administración de gimnasios con
                tecnología aplicada a necesidades reales del sector fitness.
              </p>
            </div>
            <ul className="landing-about__values">
              <li>
                <strong>Enfoque sectorial</strong>
                <span>Diseñado para operaciones de gimnasio y sucursales, no para ERP genéricos.</span>
              </li>
              <li>
                <strong>Operación simplificada</strong>
                <span>Menos fricción entre accesos, permisos y trabajo diario del equipo.</span>
              </li>
              <li>
                <strong>Crecimiento ordenado</strong>
                <span>Base multi-tenant preparada para escalar módulos sin perder control.</span>
              </li>
            </ul>
            <p className="landing-demo-note">
              Razón social, domicilio, trayectoria y testimonios: información corporativa pendiente
              de definición.
            </p>
          </div>
        </section>

        <section
          className="landing-section"
          id={LANDING_SECTION_IDS.faq}
          aria-labelledby="landing-faq-title"
        >
          <div className="landing-section__inner">
            <h2 id="landing-faq-title" className="landing-section__title">
              Preguntas frecuentes
            </h2>
            <LandingFaq />
          </div>
        </section>
      </main>
      <PublicFooter />
      <WhatsAppFloatButton />
    </div>
  );
}

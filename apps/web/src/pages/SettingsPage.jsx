import { Link } from "react-router-dom";
import HealthPanel from "../components/layout/HealthPanel.jsx";
import DemoPreferencesSection from "../components/settings/DemoPreferencesSection.jsx";
import Badge from "../components/ui/Badge.jsx";
import Card from "../components/ui/Card.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import {
  BRANCH_STATUS,
  DEMO_BRANCH_CATALOG,
} from "../demo/branches.demo.js";
import { DEMO_ORGANIZATION, DEMO_PRODUCT_INFO } from "../demo/organization.demo.js";

export default function SettingsPage() {
  const activeBranches = DEMO_BRANCH_CATALOG.filter((b) => b.status === BRANCH_STATUS.ACTIVE).length;

  return (
    <div className="settings-page demo-module-page">
      <PageHeader
        title="Configuración (demostración)"
        description="Información ficticia de la empresa, preferencias visuales locales y diagnóstico del entorno. Sin sesión, permisos ni guardado operativo."
      />

      <div className="settings-page__grid">
        <Card title="Perfil de empresa ficticia">
          <dl className="settings-dl">
            <div className="settings-dl__row">
              <dt>Razón social (demo)</dt>
              <dd>{DEMO_ORGANIZATION.legalName}</dd>
            </div>
            <div className="settings-dl__row">
              <dt>Nombre comercial</dt>
              <dd>{DEMO_ORGANIZATION.tradeName}</dd>
            </div>
            <div className="settings-dl__row">
              <dt>Descripción</dt>
              <dd>{DEMO_ORGANIZATION.description}</dd>
            </div>
            <div className="settings-dl__row">
              <dt>Zona horaria</dt>
              <dd>
                <code>{DEMO_ORGANIZATION.timezone}</code> — {DEMO_ORGANIZATION.timezoneLabel}
              </dd>
            </div>
            <div className="settings-dl__row">
              <dt>Moneda</dt>
              <dd>
                {DEMO_ORGANIZATION.currency} ({DEMO_ORGANIZATION.currencyLabel})
              </dd>
            </div>
          </dl>
          <p className="settings-section__note" role="note">
            Estos datos son de muestra. No se pueden editar ni sincronizar con MongoDB en esta fase.
          </p>
        </Card>

        <DemoPreferencesSection />

        <Card title="Sucursales del tenant (demo)">
          <p className="settings-section__intro">
            Coherente con ADR-0009: una empresa demo administra varias sucursales ficticias.
          </p>
          <ul className="settings-stats-inline">
            <li>
              <span>En catálogo</span>
              <strong>{DEMO_BRANCH_CATALOG.length}</strong>
            </li>
            <li>
              <span>Activas</span>
              <strong>{activeBranches}</strong>
            </li>
          </ul>
          <Link to="/sucursales" className="ui-btn ui-btn--primary">
            Ir a Sucursales
          </Link>
        </Card>

        <HealthPanel />

        <Card title="Información del producto">
          <p className="settings-product__head">
            <Badge variant="demo">{DEMO_PRODUCT_INFO.phase}</Badge>
          </p>
          <dl className="settings-dl">
            <div className="settings-dl__row">
              <dt>Aplicación</dt>
              <dd>{DEMO_PRODUCT_INFO.name}</dd>
            </div>
            <div className="settings-dl__row">
              <dt>Versión</dt>
              <dd>{DEMO_PRODUCT_INFO.version}</dd>
            </div>
            <div className="settings-dl__row">
              <dt>Stack</dt>
              <dd>{DEMO_PRODUCT_INFO.stackNote}</dd>
            </div>
            <div className="settings-dl__row">
              <dt>Acceso</dt>
              <dd>{DEMO_PRODUCT_INFO.authNote}</dd>
            </div>
          </dl>
        </Card>
      </div>
    </div>
  );
}

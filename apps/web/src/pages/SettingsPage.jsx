import HealthPanel from "../components/layout/HealthPanel.jsx";
import PageSection from "../components/layout/PageSection.jsx";

export default function SettingsPage() {
  return (
    <PageSection description="Preferencias de la interfaz y diagnóstico técnico. Sin autenticación ni datos operativos.">
      <div className="empty-state u-mb-6">
        <p className="empty-state__title">Configuración</p>
        <p>Opciones de la aplicación se definirán cuando exista sesión real (ADR-0003).</p>
      </div>
      <HealthPanel />
    </PageSection>
  );
}

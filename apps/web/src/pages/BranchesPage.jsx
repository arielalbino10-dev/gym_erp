import PageSection from "../components/layout/PageSection.jsx";

export default function BranchesPage() {
  return (
    <PageSection description="Sucursales del tenant. Contenido demostrativo pendiente; no sustituye permisos del backend.">
      <div className="empty-state">
        <p className="empty-state__title">Sucursales</p>
        <p>La lista de sucursales ficticias se añadirá sin implicar alcance operativo real.</p>
      </div>
    </PageSection>
  );
}

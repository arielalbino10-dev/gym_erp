import { Link } from "react-router-dom";
import PageSection from "../components/layout/PageSection.jsx";

export default function NotFoundPage() {
  return (
    <PageSection description="La ruta solicitada no existe en esta versión del ERP.">
      <div className="empty-state">
        <p className="empty-state__title">404 — Página no encontrada</p>
        <p>
          <Link to="/">Volver al Dashboard</Link>
        </p>
      </div>
    </PageSection>
  );
}

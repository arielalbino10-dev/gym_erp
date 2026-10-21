import Badge from "../ui/Badge.jsx";

/** Mock compacto y protagonista para el hero (vista demostrativa). */
export default function ProductPreviewHero() {
  return (
    <div className="landing-preview landing-preview--hero" aria-hidden="true">
      <div className="landing-preview__glow" />
      <div className="landing-preview__chrome">
        <span className="landing-preview__dot landing-preview__dot--teal" />
        <span className="landing-preview__dot" />
        <span className="landing-preview__dot" />
        <span className="landing-preview__title-bar">Gym ERP</span>
      </div>
      <div className="landing-preview__body landing-preview__body--hero">
        <div className="landing-preview__sidebar">
          <span className="landing-preview__nav-item landing-preview__nav-item--active">
            Sucursales
          </span>
          <span className="landing-preview__nav-item">Dashboard</span>
        </div>
        <div className="landing-preview__main">
          <div className="landing-preview__hero-metrics">
            <div>
              <span className="landing-preview__metric-label">Sucursales activas</span>
              <strong>3</strong>
            </div>
            <div>
              <span className="landing-preview__metric-label">Tenant</span>
              <strong>Demo</strong>
            </div>
          </div>
          <div className="landing-preview__card landing-preview__card--featured">
            <strong>Sucursal Centro</strong>
            <span>CTR-01</span>
            <Badge variant="success">Activa</Badge>
          </div>
        </div>
      </div>
    </div>
  );
}

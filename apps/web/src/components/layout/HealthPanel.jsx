import { useApiHealth } from "../../app/providers/ApiHealthProvider.jsx";
import Card from "../ui/Card.jsx";
import HealthIndicator from "./HealthIndicator.jsx";

export default function HealthPanel() {
  const { detail } = useApiHealth();

  return (
    <Card title="Estado del entorno" className="health-panel-card">
      <p className="settings-section__intro">
        Comprueba conectividad con la API de infraestructura. No valida módulos de negocio ni datos de socios.
      </p>
      <HealthIndicator compact={false} />
      <p className="health-detail" role="status" aria-live="polite">
        {detail}
      </p>
      <p className="health-hint">
        Endpoint: <code>GET /api/v1/health/ready</code>
      </p>
    </Card>
  );
}

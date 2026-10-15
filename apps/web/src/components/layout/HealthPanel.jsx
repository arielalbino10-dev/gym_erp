import { useApiHealth } from "../../app/providers/ApiHealthProvider.jsx";
import HealthIndicator from "./HealthIndicator.jsx";

export default function HealthPanel() {
  const { detail } = useApiHealth();

  return (
    <section className="card" aria-labelledby="health-panel-title">
      <h2 id="health-panel-title" className="card__title">
        Estado del sistema
      </h2>
      <HealthIndicator compact={false} />
      <p className="health-detail" role="status" aria-live="polite">
        {detail}
      </p>
      <p className="health-hint">
        Endpoint: <code>GET /api/v1/health/ready</code>
      </p>
    </section>
  );
}

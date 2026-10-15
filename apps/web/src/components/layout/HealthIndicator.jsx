import { HEALTH_STATUS, useApiHealth } from "../../app/providers/ApiHealthProvider.jsx";

export default function HealthIndicator({ compact = true }) {
  const { status, badgeLabel } = useApiHealth();

  const badgeClass =
    status === HEALTH_STATUS.ready
      ? "badge badge--ok"
      : status === HEALTH_STATUS.loading
        ? "badge badge--loading"
        : "badge badge--warn";

  if (compact) {
    return (
      <span className="health-indicator" title={`Estado API: ${badgeLabel}`}>
        <span className={`health-indicator__dot health-indicator__dot--${status}`} aria-hidden />
        <span className={`health-indicator__label ${badgeClass}`}>{badgeLabel}</span>
      </span>
    );
  }

  return <span className={badgeClass}>{badgeLabel}</span>;
}

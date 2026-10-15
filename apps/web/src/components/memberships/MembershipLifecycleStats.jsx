import Badge from "../ui/Badge.jsx";
import { MEMBERSHIP_LIFECYCLE, lifecycleLabel, lifecycleBadgeVariant } from "../../demo/memberships.demo.js";

const ORDER = [
  MEMBERSHIP_LIFECYCLE.ACTIVE,
  MEMBERSHIP_LIFECYCLE.EXPIRING,
  MEMBERSHIP_LIFECYCLE.EXPIRED,
  MEMBERSHIP_LIFECYCLE.SUSPENDED,
];

export default function MembershipLifecycleStats({ counts }) {
  return (
    <ul className="lifecycle-stats" aria-label="Resumen de estados de membresías asignadas">
      {ORDER.map((key) => (
        <li key={key} className="lifecycle-stats__item">
          <Badge variant={lifecycleBadgeVariant(key)}>{lifecycleLabel(key)}</Badge>
          <span className="lifecycle-stats__count">{counts[key] ?? 0}</span>
        </li>
      ))}
    </ul>
  );
}

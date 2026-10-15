import Badge from "../ui/Badge.jsx";
import Card from "../ui/Card.jsx";
import { membershipTypeLabel } from "../../utils/memberLabels.js";

function formatIllustrativePrice(mxn) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0,
  }).format(mxn);
}

export default function PlanCardsGrid({ plans }) {
  return (
    <div className="plan-cards">
      {plans.map((plan) => (
        <Card key={plan.planId} title={plan.name} className="plan-cards__item">
          <p className="plan-cards__meta">
            <Badge variant="demo">{plan.planCode}</Badge>
            <span className="plan-cards__type">{membershipTypeLabel(plan.membershipType)}</span>
          </p>
          <p className="plan-cards__price">
            <span className="plan-cards__price-value">{formatIllustrativePrice(plan.priceIllustrativeMxn)}</span>
            <span className="plan-cards__price-note"> precio ilustrativo / {plan.durationLabel}</span>
          </p>
          <ul className="plan-cards__highlights">
            {plan.highlights.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Card>
      ))}
    </div>
  );
}

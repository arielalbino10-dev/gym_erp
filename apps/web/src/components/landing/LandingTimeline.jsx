import { CONTRACT_STEPS } from "../../landing/landingContent.js";

export default function LandingTimeline() {
  return (
    <ol className="landing-timeline">
      {CONTRACT_STEPS.map((step, index) => (
        <li key={step.title} className="landing-timeline__step">
          <span className="landing-timeline__index" aria-hidden="true">
            {index + 1}
          </span>
          <div className="landing-timeline__body">
            <h3>{step.title}</h3>
            <p>{step.detail}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

import { LANDING_FAQ } from "../../landing/landingContent.js";

export default function LandingFaq() {
  return (
    <div className="landing-faq-accordion">
      {LANDING_FAQ.map((item) => (
        <details key={item.question} className="landing-faq-accordion__item">
          <summary>{item.question}</summary>
          <p>{item.answer}</p>
        </details>
      ))}
    </div>
  );
}

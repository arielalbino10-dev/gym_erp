const PATHS = {
  hub: "M4 12h4v8H4v-8zm6-6h4v14h-4V6zm6 3h4v11h-4V9z",
  branch:
    "M12 2 2 7v10l10 5 10-5V7L12 2zm0 2.2 7.5 3.75L12 11.7 4.5 7.95 12 4.2zM4 9.5 11 13v7.3l-7-3.5V9.5zm16 0v7.3l-7 3.5V13l7-3.5z",
  shield: "M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3zm0 2.2 6 2.25V11c0 3.8-2.5 7.3-6 8.7-3.5-1.4-6-4.9-6-8.7V6.45l6-2.25z",
  flow: "M6 4h12v2H6V4zm0 7h8v2H6v-2zm0 7h12v2H6v-2z",
  growth: "M4 18V6h2v8.6l3.5-3.5 6.3 6.3 1.4-1.4-7.7-7.7L6 13.4V18H4z",
  insight:
    "M4 5h16v2H4V5zm0 6h10v2H4v-2zm0 6h16v2H4v-2zm12-5 3 3-5 5-3-3 5-5z",
};

export default function LandingIcon({ name, className = "" }) {
  const d = PATHS[name] || PATHS.hub;
  return (
    <svg
      className={`landing-icon ${className}`.trim()}
      width="28"
      height="28"
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path fill="currentColor" d={d} />
    </svg>
  );
}

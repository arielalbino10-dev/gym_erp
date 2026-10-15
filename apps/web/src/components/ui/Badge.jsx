export default function Badge({ children, variant = "neutral" }) {
  return <span className={`ui-badge ui-badge--${variant}`}>{children}</span>;
}

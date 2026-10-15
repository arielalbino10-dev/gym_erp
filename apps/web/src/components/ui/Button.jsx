export default function Button({
  children,
  variant = "secondary",
  type = "button",
  pressed,
  className = "",
  ...rest
}) {
  const isToggle = typeof pressed === "boolean";
  return (
    <button
      type={type}
      className={`ui-btn ui-btn--${variant} ${className}`.trim()}
      aria-pressed={isToggle ? pressed : undefined}
      {...rest}
    >
      {children}
    </button>
  );
}

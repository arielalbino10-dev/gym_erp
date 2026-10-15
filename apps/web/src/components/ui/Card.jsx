export default function Card({ title, titleId, children, className = "" }) {
  const headingId = titleId || (title ? `card-title-${title.replace(/\s+/g, "-").toLowerCase()}` : undefined);

  return (
    <section
      className={`ui-card ${className}`.trim()}
      aria-labelledby={headingId}
    >
      {title ? (
        <h2 id={headingId} className="ui-card__title">
          {title}
        </h2>
      ) : null}
      {children}
    </section>
  );
}

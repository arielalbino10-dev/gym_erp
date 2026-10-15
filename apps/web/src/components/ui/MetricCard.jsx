import Badge from "./Badge.jsx";

export default function MetricCard({ title, value, footnote, loading = false }) {
  if (loading) {
    return (
      <article className="metric-card metric-card--loading" aria-busy="true" aria-label={title}>
        <div className="metric-card__skeleton metric-card__skeleton--title" />
        <div className="metric-card__skeleton metric-card__skeleton--value" />
        <div className="metric-card__skeleton metric-card__skeleton--foot" />
      </article>
    );
  }

  return (
    <article className="metric-card">
      <div className="metric-card__head">
        <h3 className="metric-card__title">{title}</h3>
        <Badge variant="demo">Demo</Badge>
      </div>
      <p className="metric-card__value">{value}</p>
      {footnote ? <p className="metric-card__footnote">{footnote}</p> : null}
    </article>
  );
}

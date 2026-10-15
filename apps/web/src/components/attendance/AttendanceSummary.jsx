import { formatDemoDate } from "../../utils/memberLabels.js";

export default function AttendanceSummary({ summary }) {
  const branchEntries = Object.entries(summary.byBranch || {});
  return (
    <section className="attendance-summary" aria-labelledby="attendance-summary-title">
      <h3 id="attendance-summary-title" className="attendance-summary__title">
        Resumen del periodo filtrado
      </h3>
      <dl className="attendance-summary__grid">
        <div>
          <dt>Entradas registradas</dt>
          <dd>{summary.totalEntries}</dd>
        </div>
        <div>
          <dt>Socios distintos</dt>
          <dd>{summary.uniqueMembers}</dd>
        </div>
        <div>
          <dt>Desde</dt>
          <dd>{summary.periodFrom ? formatDemoDate(summary.periodFrom) : "—"}</dd>
        </div>
        <div>
          <dt>Hasta</dt>
          <dd>{summary.periodTo ? formatDemoDate(summary.periodTo) : "—"}</dd>
        </div>
      </dl>
      {branchEntries.length > 0 ? (
        <ul className="attendance-summary__branches">
          {branchEntries.map(([name, count]) => (
            <li key={name}>
              <span className="attendance-summary__branch-name">{name}</span>
              <span className="attendance-summary__branch-count">{count} entradas</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

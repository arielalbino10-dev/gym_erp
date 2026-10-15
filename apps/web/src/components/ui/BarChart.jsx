import { useId, useState } from "react";
import EmptyState from "./EmptyState.jsx";

/**
 * Gráfico de barras SVG accesible (sin librerías externas).
 * @param {{ data: Array<{ labelShort: string, labelLong: string, count: number, dateIso: string }>, title: string }}
 */
export default function BarChart({ data, title }) {
  const chartId = useId();
  const tableId = `${chartId}-table`;
  const [focusedIndex, setFocusedIndex] = useState(null);

  const tooltipText =
    focusedIndex !== null
      ? `${data[focusedIndex].labelLong}: ${data[focusedIndex].count} asistencias (demo)`
      : "Enfoque una barra para ver el detalle por fecha.";

  if (!data.length) {
    return (
      <EmptyState title="Sin datos para el periodo">
        <p>Seleccione otro rango o vuelva más tarde (solo demo).</p>
      </EmptyState>
    );
  }

  const max = Math.max(...data.map((d) => d.count), 1);
  const chartHeight = 160;
  const barGap = 8;
  const barWidth = Math.min(28, Math.max(12, (320 - barGap * data.length) / data.length));

  return (
    <div className="bar-chart">
      <div className="bar-chart__header">
        <p id={chartId} className="bar-chart__title">
          {title}
        </p>
        <p className="bar-chart__tooltip" role="status" aria-live="polite">
          {tooltipText}
        </p>
      </div>

      <div className="bar-chart__plot" role="group" aria-labelledby={chartId}>
        <svg
          className="bar-chart__svg"
          viewBox={`0 0 ${data.length * (barWidth + barGap) + barGap} ${chartHeight + 24}`}
          preserveAspectRatio="xMidYMid meet"
          aria-hidden="true"
        >
          {data.map((point, index) => {
            const height = (point.count / max) * chartHeight;
            const x = barGap + index * (barWidth + barGap);
            const y = chartHeight - height;
            return (
              <g key={point.dateIso}>
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={height}
                  rx={4}
                  className={
                    focusedIndex === index ? "bar-chart__bar bar-chart__bar--focus" : "bar-chart__bar"
                  }
                />
                <text
                  x={x + barWidth / 2}
                  y={chartHeight + 16}
                  textAnchor="middle"
                  className="bar-chart__label"
                >
                  {point.labelShort}
                </text>
              </g>
            );
          })}
        </svg>
        <div className="bar-chart__bars-a11y">
          {data.map((point, index) => (
            <button
              key={point.dateIso}
              type="button"
              className={
                focusedIndex === index ? "bar-chart__bar-btn bar-chart__bar-btn--active" : "bar-chart__bar-btn"
              }
              aria-label={`${point.labelLong}: ${point.count} asistencias demo`}
              onFocus={() => setFocusedIndex(index)}
              onBlur={() => setFocusedIndex(null)}
              onMouseEnter={() => setFocusedIndex(index)}
              onMouseLeave={() => setFocusedIndex(null)}
            >
              <span className="visually-hidden">{point.labelLong}</span>
              <span className="bar-chart__bar-btn-value" aria-hidden>
                {point.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      <details className="bar-chart__table-toggle">
        <summary>Ver datos del gráfico como tabla</summary>
        <table id={tableId} className="bar-chart__table">
          <caption>{title} — resumen accesible</caption>
          <thead>
            <tr>
              <th scope="col">Fecha</th>
              <th scope="col">Asistencias (demo)</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.dateIso}>
                <td>{row.labelLong}</td>
                <td>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}

import { Link } from "react-router-dom";
import Button from "../ui/Button.jsx";
import { formatDemoDate } from "../../utils/memberLabels.js";

export const ATTENDANCE_SORT = {
  DATETIME: "datetime",
};

function SortButton({ label, field, activeField, direction, onSort }) {
  const active = activeField === field;
  const sortHint = active ? (direction === "asc" ? "ascendente" : "descendente") : "sin orden";
  return (
    <Button
      type="button"
      variant="ghost"
      className="demo-data-table__sort"
      onClick={() => onSort(field)}
      aria-label={`Ordenar por ${label}, ${sortHint}`}
    >
      {label}
      {active ? <span aria-hidden="true">{direction === "asc" ? " ↑" : " ↓"}</span> : null}
    </Button>
  );
}

export default function AttendanceRecordsTable({ rows, sortField, sortDir, onSort, onViewDetail }) {
  return (
    <div className="demo-data-table-wrap">
      <table className="demo-data-table">
        <caption className="visually-hidden">Registros de asistencia ficticios</caption>
        <thead>
          <tr>
            <th
              scope="col"
              aria-sort={sortField === ATTENDANCE_SORT.DATETIME ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
            >
              <SortButton
                label="Fecha y hora"
                field={ATTENDANCE_SORT.DATETIME}
                activeField={sortField}
                direction={sortDir}
                onSort={onSort}
              />
            </th>
            <th scope="col">Socio</th>
            <th scope="col" className="demo-data-table__hide-sm">
              Código
            </th>
            <th scope="col">Sucursal demo</th>
            <th scope="col" className="demo-data-table__hide-md">
              Método
            </th>
            <th scope="col">
              <span className="visually-hidden">Acciones</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.recordId}>
              <td data-label="Fecha y hora">
                {formatDemoDate(row.dateIso)} · {row.timeLocal}
              </td>
              <td data-label="Socio">
                <Link to="/socios" className="demo-data-table__link" aria-label={`${row.fullName}, ir a socios demo`}>
                  {row.fullName}
                </Link>
              </td>
              <td data-label="Código" className="demo-data-table__hide-sm">
                <code>{row.memberCode}</code>
              </td>
              <td data-label="Sucursal">{row.branchName}</td>
              <td data-label="Método" className="demo-data-table__hide-md">
                {row.accessMethodLabel}
              </td>
              <td data-label="Acciones">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => onViewDetail(row)}
                  aria-label={`Ver detalle de asistencia de ${row.fullName} el ${row.dateIso}`}
                >
                  Ver detalle
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

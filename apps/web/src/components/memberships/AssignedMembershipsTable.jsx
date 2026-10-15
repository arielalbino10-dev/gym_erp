import { Link } from "react-router-dom";
import Badge from "../ui/Badge.jsx";
import Button from "../ui/Button.jsx";
import { lifecycleBadgeVariant, lifecycleLabel } from "../../demo/memberships.demo.js";
import { formatDemoDate, membershipTypeLabel } from "../../utils/memberLabels.js";

export const MEMBERSHIP_SORT = {
  START: "startDate",
  END: "endDate",
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

export default function AssignedMembershipsTable({ rows, sortField, sortDir, onSort, onViewDetail }) {
  return (
    <div className="demo-data-table-wrap">
      <table className="demo-data-table">
        <caption className="visually-hidden">Membresías asignadas a socios ficticios</caption>
        <thead>
          <tr>
            <th scope="col">Socio</th>
            <th scope="col" className="demo-data-table__hide-sm">
              Código
            </th>
            <th scope="col">Plan</th>
            <th scope="col">Estado</th>
            <th
              scope="col"
              className="demo-data-table__hide-md"
              aria-sort={
                sortField === MEMBERSHIP_SORT.START ? (sortDir === "asc" ? "ascending" : "descending") : "none"
              }
            >
              <SortButton
                label="Inicio"
                field={MEMBERSHIP_SORT.START}
                activeField={sortField}
                direction={sortDir}
                onSort={onSort}
              />
            </th>
            <th
              scope="col"
              aria-sort={sortField === MEMBERSHIP_SORT.END ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
            >
              <SortButton
                label="Vencimiento"
                field={MEMBERSHIP_SORT.END}
                activeField={sortField}
                direction={sortDir}
                onSort={onSort}
              />
            </th>
            <th scope="col">
              <span className="visually-hidden">Acciones</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.assignmentId}>
              <td data-label="Socio">
                <Link to="/socios" className="demo-data-table__link" aria-label={`${row.fullName}, ir a socios demo`}>
                  {row.fullName}
                </Link>
              </td>
              <td data-label="Código" className="demo-data-table__hide-sm">
                <code>{row.memberCode}</code>
              </td>
              <td data-label="Plan">{membershipTypeLabel(row.membershipType)}</td>
              <td data-label="Estado">
                <Badge variant={lifecycleBadgeVariant(row.lifecycle)}>{lifecycleLabel(row.lifecycle)}</Badge>
              </td>
              <td data-label="Inicio" className="demo-data-table__hide-md">
                {formatDemoDate(row.startDate)}
              </td>
              <td data-label="Vencimiento">{formatDemoDate(row.endDate)}</td>
              <td data-label="Acciones">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => onViewDetail(row)}
                  aria-label={`Ver detalle de membresía de ${row.fullName}, ${row.memberCode}`}
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

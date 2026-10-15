import Badge from "../ui/Badge.jsx";
import Button from "../ui/Button.jsx";
import { SORT_FIELDS } from "../../hooks/useMemberListState.js";
import {
  formatDemoDate,
  memberStatusBadgeVariant,
  memberStatusLabel,
  membershipTypeLabel,
} from "../../utils/memberLabels.js";

function SortButton({ label, field, activeField, direction, onSort }) {
  const active = activeField === field;
  const sortHint = active ? (direction === "asc" ? "ascendente" : "descendente") : "sin orden";
  return (
    <Button
      type="button"
      variant="ghost"
      className="members-table__sort"
      onClick={() => onSort(field)}
      aria-label={`Ordenar por ${label}, ${sortHint}`}
    >
      {label}
      {active ? <span aria-hidden="true">{direction === "asc" ? " ↑" : " ↓"}</span> : null}
    </Button>
  );
}

export default function MembersTable({ rows, sortField, sortDir, onSort, onViewDetail }) {
  return (
    <div className="members-table-wrap">
      <table className="members-table">
        <caption className="visually-hidden">
          Listado de socios de demostración con código, contacto, plan y estado
        </caption>
        <thead>
          <tr>
            <th scope="col">Código</th>
            <th scope="col" aria-sort={sortField === SORT_FIELDS.NAME ? (sortDir === "asc" ? "ascending" : "descending") : "none"}>
              <SortButton
                label="Nombre"
                field={SORT_FIELDS.NAME}
                activeField={sortField}
                direction={sortDir}
                onSort={onSort}
              />
            </th>
            <th scope="col" className="members-table__hide-sm">
              Teléfono
            </th>
            <th scope="col">Plan</th>
            <th scope="col">Estado</th>
            <th
              scope="col"
              className="members-table__hide-md"
              aria-sort={sortField === SORT_FIELDS.ENROLLED ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
            >
              <SortButton
                label="Inscripción"
                field={SORT_FIELDS.ENROLLED}
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
          {rows.map((member) => (
            <tr key={member.memberId}>
              <td data-label="Código">
                <code className="members-table__code">{member.memberCode}</code>
              </td>
              <td data-label="Nombre">{member.fullName}</td>
              <td data-label="Teléfono" className="members-table__hide-sm">
                {member.phone}
              </td>
              <td data-label="Plan">{membershipTypeLabel(member.membershipType)}</td>
              <td data-label="Estado">
                <Badge variant={memberStatusBadgeVariant(member.status)}>
                  {memberStatusLabel(member.status)}
                </Badge>
              </td>
              <td data-label="Inscripción" className="members-table__hide-md">
                {formatDemoDate(member.enrolledOn)}
              </td>
              <td data-label="Acciones">
                <Button type="button" variant="secondary" onClick={() => onViewDetail(member)}>
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

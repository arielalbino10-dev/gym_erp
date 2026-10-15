import SelectInput from "../ui/SelectInput.jsx";
import TextInput from "../ui/TextInput.jsx";
import Button from "../ui/Button.jsx";
import { SORT_FIELDS } from "../../hooks/useMemberListState.js";
import {
  MEMBER_STATUS_FILTER_OPTIONS,
  MEMBERSHIP_FILTER_OPTIONS,
} from "../../demo/members.demo.js";

export default function MembersToolbar({
  query,
  onQueryChange,
  statusFilter,
  onStatusFilterChange,
  membershipFilter,
  onMembershipFilterChange,
  totalCount,
  sortField,
  sortDir,
  onSort,
}) {
  return (
    <div className="members-toolbar">
      <div className="members-toolbar__search">
        <label className="members-toolbar__label" htmlFor="members-search">
          Buscar por nombre o código
        </label>
        <TextInput
          id="members-search"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Ej. Socio ficticio o DEMO-M-001"
        />
      </div>
      <div className="members-toolbar__filters">
        <div className="members-toolbar__filter">
          <label className="members-toolbar__label" htmlFor="members-filter-status">
            Estado
          </label>
          <SelectInput
            id="members-filter-status"
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value)}
            options={MEMBER_STATUS_FILTER_OPTIONS}
          />
        </div>
        <div className="members-toolbar__filter">
          <label className="members-toolbar__label" htmlFor="members-filter-plan">
            Membresía
          </label>
          <SelectInput
            id="members-filter-plan"
            value={membershipFilter}
            onChange={(e) => onMembershipFilterChange(e.target.value)}
            options={MEMBERSHIP_FILTER_OPTIONS}
          />
        </div>
      </div>
      <div className="members-toolbar__sort-mobile" role="group" aria-label="Ordenar listado">
        <span className="members-toolbar__label">Ordenar por</span>
        <div className="members-toolbar__sort-buttons">
          <Button
            type="button"
            variant={sortField === SORT_FIELDS.NAME ? "primary" : "secondary"}
            pressed={sortField === SORT_FIELDS.NAME}
            onClick={() => onSort(SORT_FIELDS.NAME)}
          >
            Nombre {sortField === SORT_FIELDS.NAME ? (sortDir === "asc" ? "↑" : "↓") : ""}
          </Button>
          <Button
            type="button"
            variant={sortField === SORT_FIELDS.ENROLLED ? "primary" : "secondary"}
            pressed={sortField === SORT_FIELDS.ENROLLED}
            onClick={() => onSort(SORT_FIELDS.ENROLLED)}
          >
            Inscripción {sortField === SORT_FIELDS.ENROLLED ? (sortDir === "asc" ? "↑" : "↓") : ""}
          </Button>
        </div>
      </div>
      <p className="members-toolbar__count" aria-live="polite">
        {totalCount === 1 ? "1 resultado" : `${totalCount} resultados`}
      </p>
    </div>
  );
}

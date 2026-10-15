import Button from "./Button.jsx";
import SelectInput from "./SelectInput.jsx";
import TextInput from "./TextInput.jsx";

/**
 * Barra reutilizable: búsqueda, filtros select, orden móvil opcional y contador.
 */
export default function ListToolbar({
  searchId,
  searchLabel,
  searchPlaceholder,
  query,
  onQueryChange,
  filters = [],
  totalCount,
  sortMobile,
}) {
  return (
    <div className="list-toolbar">
      <div className="list-toolbar__search">
        <label className="list-toolbar__label" htmlFor={searchId}>
          {searchLabel}
        </label>
        <TextInput
          id={searchId}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={searchPlaceholder}
        />
      </div>
      {filters.length > 0 ? (
        <div className="list-toolbar__filters">
          {filters.map((f) => (
            <div key={f.id} className="list-toolbar__filter">
              <label className="list-toolbar__label" htmlFor={f.id}>
                {f.label}
              </label>
              <SelectInput id={f.id} value={f.value} onChange={(e) => f.onChange(e.target.value)} options={f.options} />
            </div>
          ))}
        </div>
      ) : null}
      {sortMobile ? (
        <div className="list-toolbar__sort-mobile" role="group" aria-label={sortMobile.groupLabel}>
          <span className="list-toolbar__label">{sortMobile.groupLabel}</span>
          <div className="list-toolbar__sort-buttons">
            {sortMobile.fields.map((field) => (
              <Button
                key={field.key}
                type="button"
                variant={sortMobile.sortField === field.key ? "primary" : "secondary"}
                pressed={sortMobile.sortField === field.key}
                onClick={() => sortMobile.onSort(field.key)}
              >
                {field.label}
                {sortMobile.sortField === field.key ? (sortMobile.sortDir === "asc" ? " ↑" : " ↓") : ""}
              </Button>
            ))}
          </div>
        </div>
      ) : null}
      <p className="list-toolbar__count" aria-live="polite">
        {totalCount === 1 ? "1 resultado" : `${totalCount} resultados`}
      </p>
    </div>
  );
}

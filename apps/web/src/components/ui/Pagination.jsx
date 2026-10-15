import { useId } from "react";
import Button from "./Button.jsx";

export default function Pagination({
  page,
  pageCount,
  pageSize,
  pageSizeOptions,
  onPageChange,
  onPageSizeChange,
}) {
  const pageSizeId = useId();
  if (pageCount <= 0) {
    return null;
  }

  return (
    <nav className="pagination" aria-label="Paginación de resultados">
      <div className="pagination__size">
        <label className="pagination__size-label" htmlFor={pageSizeId}>
          Filas por página
        </label>
        <select
          id={pageSizeId}
          className="ui-select pagination__select"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
        >
          {pageSizeOptions.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </div>
      <div className="pagination__controls">
        <Button type="button" variant="secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Anterior
        </Button>
        <span className="pagination__status" aria-live="polite">
          Página {page} de {pageCount}
        </span>
        <Button
          type="button"
          variant="secondary"
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
        >
          Siguiente
        </Button>
      </div>
    </nav>
  );
}

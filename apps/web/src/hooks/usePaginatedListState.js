import { useMemo, useState } from "react";

/**
 * Estado genérico: filtro, orden y paginación local (sin duplicar lógica por módulo).
 * @param {Array} items
 * @param {{ filterItem: Function, compareItems: Function, defaultSortField: string, defaultSortDir?: string, defaultPageSize?: number }} options
 */
export function usePaginatedListState(items, options) {
  const {
    filterItem,
    compareItems,
    defaultSortField,
    defaultSortDir = "desc",
    defaultPageSize = 10,
  } = options;

  const [query, setQueryState] = useState("");
  const [filters, setFiltersState] = useState({});
  const [sortField, setSortField] = useState(defaultSortField);
  const [sortDir, setSortDir] = useState(defaultSortDir);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSizeState] = useState(defaultPageSize);

  const filtered = useMemo(
    () => items.filter((item) => filterItem(item, { query, filters })),
    [items, query, filters, filterItem],
  );

  const sorted = useMemo(() => {
    const list = [...filtered];
    list.sort((a, b) => compareItems(a, b, sortField, sortDir));
    return list;
  }, [filtered, sortField, sortDir, compareItems]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize) || 1);
  const safePage = Math.min(page, pageCount);

  const pageSlice = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [sorted, safePage, pageSize]);

  function toggleSort(field) {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir(defaultSortDir);
    }
  }

  function setQuery(value) {
    setQueryState(value);
    setPage(1);
  }

  function setFilter(key, value) {
    setFiltersState((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  }

  function setPageSize(size) {
    setPageSizeState(size);
    setPage(1);
  }

  const hasActiveFilters =
    Boolean(query.trim()) || Object.values(filters).some((v) => v !== "" && v != null);

  return {
    query,
    setQuery,
    filters,
    setFilter,
    sortField,
    sortDir,
    toggleSort,
    page: safePage,
    setPage,
    pageSize,
    setPageSize,
    totalCount: sorted.length,
    pageCount,
    pageSlice,
    hasActiveFilters,
  };
}

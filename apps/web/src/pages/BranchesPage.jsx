import { useMemo, useState } from "react";
import BranchDetailModal from "../components/branches/BranchDetailModal.jsx";
import BranchesGrid from "../components/branches/BranchesGrid.jsx";
import Card from "../components/ui/Card.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ListToolbar from "../components/ui/ListToolbar.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Pagination from "../components/ui/Pagination.jsx";
import {
  BRANCHES_PAGE_SIZE_OPTIONS,
  BRANCH_STATUS,
  BRANCH_STATUS_FILTER_OPTIONS,
  DEMO_BRANCH_CATALOG,
  countDemoMembersByBranchId,
} from "../demo/branches.demo.js";
import { DEMO_MEMBERS } from "../demo/members.demo.js";
import { usePaginatedListState } from "../hooks/usePaginatedListState.js";

function filterBranch(item, { query, filters }) {
  if (filters.status && item.status !== filters.status) {
    return false;
  }
  const q = query.trim().toLowerCase();
  if (!q) {
    return true;
  }
  return item.name.toLowerCase().includes(q) || item.branchCode.toLowerCase().includes(q);
}

function compareBranches(a, b) {
  return a.name.localeCompare(b.name, "es");
}

const listOptions = {
  filterItem: filterBranch,
  compareItems: (a, b, _field, sortDir) => {
    const cmp = compareBranches(a, b);
    return sortDir === "asc" ? cmp : -cmp;
  },
  defaultSortField: "name",
  defaultSortDir: "asc",
  defaultPageSize: 4,
};

export default function BranchesPage() {
  const [detailBranch, setDetailBranch] = useState(null);
  const memberCounts = useMemo(() => countDemoMembersByBranchId(DEMO_MEMBERS), []);

  const summary = useMemo(() => {
    const active = DEMO_BRANCH_CATALOG.filter((b) => b.status === BRANCH_STATUS.ACTIVE).length;
    const inactive = DEMO_BRANCH_CATALOG.length - active;
    return { total: DEMO_BRANCH_CATALOG.length, active, inactive };
  }, []);

  const list = usePaginatedListState(DEMO_BRANCH_CATALOG, listOptions);

  const detailMemberCount = detailBranch ? memberCounts[detailBranch.branchId] ?? 0 : 0;

  return (
    <div className="demo-module-page branches-page">
      <PageHeader
        title="Sucursales (demostración)"
        description="Catálogo ficticio multi-sucursal alineado con ADR-0009. Sin altas, bajas ni permisos reales."
      />

      <Card title="Resumen del catálogo demo" className="branches-page__summary">
        <ul className="branches-page__stats">
          <li>
            <span>Total en catálogo</span>
            <strong>{summary.total}</strong>
          </li>
          <li>
            <span>Activas</span>
            <strong>{summary.active}</strong>
          </li>
          <li>
            <span>Inactivas (ejemplo)</span>
            <strong>{summary.inactive}</strong>
          </li>
        </ul>
      </Card>

      <Card title="Sucursales ficticias" className="demo-module-page__card">
        <ListToolbar
          searchId="branches-search"
          searchLabel="Buscar por nombre o código"
          searchPlaceholder="Centro Demo o SUC-CEN"
          query={list.query}
          onQueryChange={list.setQuery}
          filters={[
            {
              id: "branches-filter-status",
              label: "Estado",
              value: list.filters.status ?? "",
              onChange: (v) => list.setFilter("status", v),
              options: BRANCH_STATUS_FILTER_OPTIONS,
            },
          ]}
          totalCount={list.totalCount}
        />

        {list.totalCount === 0 ? (
          <EmptyState title={list.hasActiveFilters ? "Sin coincidencias" : "Sin sucursales demo"}>
            {list.hasActiveFilters ? (
              <p>Ajuste la búsqueda o el filtro de estado.</p>
            ) : (
              <p>No hay sucursales en el catálogo de demostración.</p>
            )}
          </EmptyState>
        ) : (
          <>
            <BranchesGrid
              branches={list.pageSlice}
              memberCounts={memberCounts}
              onViewDetail={setDetailBranch}
            />
            <Pagination
              page={list.page}
              pageCount={list.pageCount}
              pageSize={list.pageSize}
              pageSizeOptions={BRANCHES_PAGE_SIZE_OPTIONS}
              onPageChange={list.setPage}
              onPageSizeChange={list.setPageSize}
            />
          </>
        )}
      </Card>

      <BranchDetailModal
        branch={detailBranch}
        memberCount={detailMemberCount}
        onClose={() => setDetailBranch(null)}
      />
    </div>
  );
}

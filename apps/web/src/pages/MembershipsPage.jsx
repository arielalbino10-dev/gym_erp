import { useMemo, useState } from "react";
import DemoBranchScopeBanner from "../components/layout/DemoBranchScopeBanner.jsx";
import { useBranchScopedItems } from "../hooks/useBranchScopedItems.js";
import AssignedMembershipsTable, {
  MEMBERSHIP_SORT,
} from "../components/memberships/AssignedMembershipsTable.jsx";
import MembershipDetailModal from "../components/memberships/MembershipDetailModal.jsx";
import MembershipLifecycleStats from "../components/memberships/MembershipLifecycleStats.jsx";
import PlanCardsGrid from "../components/memberships/PlanCardsGrid.jsx";
import Card from "../components/ui/Card.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ListToolbar from "../components/ui/ListToolbar.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Pagination from "../components/ui/Pagination.jsx";
import {
  DEMO_ASSIGNED_MEMBERSHIPS,
  DEMO_MEMBERSHIP_PLANS,
  LIFECYCLE_FILTER_OPTIONS,
  MEMBERSHIPS_PAGE_SIZE_OPTIONS,
  PLAN_FILTER_OPTIONS,
  countByLifecycle,
} from "../demo/memberships.demo.js";
import { usePaginatedListState } from "../hooks/usePaginatedListState.js";

function filterAssignment(item, { query, filters }) {
  const q = query.trim().toLowerCase();
  if (filters.plan && item.membershipType !== filters.plan) {
    return false;
  }
  if (filters.lifecycle && item.lifecycle !== filters.lifecycle) {
    return false;
  }
  if (!q) {
    return true;
  }
  return item.fullName.toLowerCase().includes(q) || item.memberCode.toLowerCase().includes(q);
}

function compareAssignments(a, b, sortField, sortDir) {
  let cmp = 0;
  if (sortField === MEMBERSHIP_SORT.START) {
    cmp = a.startDate.localeCompare(b.startDate);
  } else {
    cmp = a.endDate.localeCompare(b.endDate);
  }
  return sortDir === "asc" ? cmp : -cmp;
}

const listOptions = {
  filterItem: filterAssignment,
  compareItems: compareAssignments,
  defaultSortField: MEMBERSHIP_SORT.END,
  defaultSortDir: "desc",
  defaultPageSize: 10,
};

export default function MembershipsPage() {
  const [detailRow, setDetailRow] = useState(null);
  const assignments = useMemo(() => DEMO_ASSIGNED_MEMBERSHIPS, []);
  const branchScopedAssignments = useBranchScopedItems(assignments);
  const lifecycleCounts = useMemo(() => countByLifecycle(branchScopedAssignments), [branchScopedAssignments]);

  const list = usePaginatedListState(branchScopedAssignments, listOptions);

  return (
    <div className="demo-module-page">
      <PageHeader
        title="Membresías (demostración)"
        description="Catálogo de planes ilustrativos y membresías asignadas a socios ficticios. Sin cobros, renovaciones ni contabilidad."
      />

      <DemoBranchScopeBanner />

      <section aria-labelledby="plans-section-title">
        <h3 id="plans-section-title" className="demo-module-page__section-title">
          Planes disponibles (catálogo demo)
        </h3>
        <PlanCardsGrid plans={DEMO_MEMBERSHIP_PLANS} />
      </section>

      <Card title="Membresías asignadas a socios" className="demo-module-page__card">
        <MembershipLifecycleStats counts={lifecycleCounts} />

        <ListToolbar
          searchId="memberships-search"
          searchLabel="Buscar por socio o código"
          searchPlaceholder="Nombre o DEMO-M-…"
          query={list.query}
          onQueryChange={list.setQuery}
          filters={[
            {
              id: "memberships-filter-plan",
              label: "Plan",
              value: list.filters.plan ?? "",
              onChange: (v) => list.setFilter("plan", v),
              options: PLAN_FILTER_OPTIONS,
            },
            {
              id: "memberships-filter-lifecycle",
              label: "Estado",
              value: list.filters.lifecycle ?? "",
              onChange: (v) => list.setFilter("lifecycle", v),
              options: LIFECYCLE_FILTER_OPTIONS,
            },
          ]}
          totalCount={list.totalCount}
          sortMobile={{
            groupLabel: "Ordenar por fecha",
            sortField: list.sortField,
            sortDir: list.sortDir,
            onSort: list.toggleSort,
            fields: [
              { key: MEMBERSHIP_SORT.START, label: "Inicio" },
              { key: MEMBERSHIP_SORT.END, label: "Vencimiento" },
            ],
          }}
        />

        {list.totalCount === 0 ? (
          <EmptyState title={list.hasActiveFilters ? "Sin coincidencias" : "Sin membresías de demostración"}>
            {list.hasActiveFilters ? (
              <p>Ajuste la búsqueda o los filtros para ver otras asignaciones ficticias.</p>
            ) : (
              <p>No hay asignaciones demo en esta vista.</p>
            )}
          </EmptyState>
        ) : (
          <>
            <AssignedMembershipsTable
              rows={list.pageSlice}
              sortField={list.sortField}
              sortDir={list.sortDir}
              onSort={list.toggleSort}
              onViewDetail={setDetailRow}
            />
            <Pagination
              page={list.page}
              pageCount={list.pageCount}
              pageSize={list.pageSize}
              pageSizeOptions={MEMBERSHIPS_PAGE_SIZE_OPTIONS}
              onPageChange={list.setPage}
              onPageSizeChange={list.setPageSize}
            />
          </>
        )}
      </Card>

      <MembershipDetailModal assignment={detailRow} onClose={() => setDetailRow(null)} />
    </div>
  );
}

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import BranchDetailModal from "../components/branches/BranchDetailModal.jsx";
import BranchesGrid from "../components/branches/BranchesGrid.jsx";
import CreateBranchForm from "../components/branches/CreateBranchForm.jsx";
import { useGymAuth } from "../app/providers/GymAuthProvider.jsx";
import {
  canCreateBranchesFromSession,
  createGymBranch,
  listGymBranches,
  mapApiBranchToUi,
} from "../api/gymBranchesApi.js";
import { GymApiError } from "../api/gymHttpClient.js";
import Card from "../components/ui/Card.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ListToolbar from "../components/ui/ListToolbar.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Pagination from "../components/ui/Pagination.jsx";
import {
  BRANCHES_PAGE_SIZE_OPTIONS,
  BRANCH_STATUS,
  BRANCH_STATUS_FILTER_OPTIONS,
  branchStatusBadgeVariant,
  branchStatusLabel,
} from "../demo/branches.demo.js";
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
  defaultPageSize: 6,
};

export default function BranchesPage() {
  const {
    session,
    operationalGeneration,
    beginOperationalRequest,
    isOperationalResponseStale,
  } = useGymAuth();
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [detailBranch, setDetailBranch] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const loadSeqRef = useRef(0);

  const canCreate = canCreateBranchesFromSession(session);

  useEffect(() => {
    setBranches([]);
    setLoadError(null);
    setDetailBranch(null);
    setSuccessMessage(null);
  }, [session?.active_tenant_id, operationalGeneration]);

  const reload = useCallback(async () => {
    const loadSeq = ++loadSeqRef.current;
    const { generation, signal } = beginOperationalRequest();
    setLoadError(null);
    setLoading(true);
    try {
      const rows = await listGymBranches({ signal });
      if (loadSeq !== loadSeqRef.current || isOperationalResponseStale(generation)) {
        return;
      }
      setBranches(rows.map(mapApiBranchToUi));
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      if (loadSeq !== loadSeqRef.current || isOperationalResponseStale(generation)) {
        return;
      }
      setLoadError(err instanceof GymApiError ? err.message : "No se pudieron cargar sucursales.");
      setBranches([]);
    } finally {
      if (loadSeq === loadSeqRef.current && !isOperationalResponseStale(generation)) {
        setLoading(false);
      }
    }
  }, [beginOperationalRequest, isOperationalResponseStale]);

  useEffect(() => {
    reload();
  }, [reload, session?.active_tenant_id, operationalGeneration]);

  const summary = useMemo(() => {
    const active = branches.filter((b) => b.status === BRANCH_STATUS.ACTIVE).length;
    return { total: branches.length, active, inactive: branches.length - active };
  }, [branches]);

  const list = usePaginatedListState(branches, listOptions);

  async function handleCreate(payload) {
    const { generation, signal } = beginOperationalRequest();
    setCreateError(null);
    setSuccessMessage(null);
    setCreateBusy(true);
    try {
      await createGymBranch(payload, { signal });
      if (isOperationalResponseStale(generation)) {
        return;
      }
      setSuccessMessage("Sucursal creada correctamente.");
      await reload();
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      if (isOperationalResponseStale(generation)) {
        return;
      }
      setCreateError(err instanceof GymApiError ? err.message : "No se pudo crear la sucursal.");
    } finally {
      if (!isOperationalResponseStale(generation)) {
        setCreateBusy(false);
      }
    }
  }

  return (
    <div className="demo-module-page branches-page">
      <PageHeader
        title="Sucursales"
        description={
          session?.tenant_display_name
            ? `Gimnasio activo: ${session.tenant_display_name}. Datos desde MongoDB operational.`
            : "Listado operativo de sucursales autorizadas."
        }
      />

      {successMessage ? (
        <p className="branches-page__success" role="status">
          {successMessage}
        </p>
      ) : null}

      <Card title="Resumen" className="branches-page__summary">
        <ul className="branches-page__stats">
          <li>
            <span>Total</span>
            <strong>{summary.total}</strong>
          </li>
          <li>
            <span>Activas</span>
            <strong>{summary.active}</strong>
          </li>
          <li>
            <span>Otras</span>
            <strong>{summary.inactive}</strong>
          </li>
        </ul>
      </Card>

      {canCreate ? (
        <Card title="Nueva sucursal" className="demo-module-page__card">
          <CreateBranchForm onSubmit={handleCreate} busy={createBusy} error={createError} />
        </Card>
      ) : (
        <Card title="Alta de sucursales" className="demo-module-page__card">
          <p>Su rol no incluye permiso para crear sucursales. El servidor rechazará intentos no autorizados.</p>
        </Card>
      )}

      <Card title="Sucursales del gimnasio" className="demo-module-page__card">
        {loading ? (
          <p>Cargando sucursales…</p>
        ) : loadError ? (
          <EmptyState title="Error al cargar">
            <p>{loadError}</p>
          </EmptyState>
        ) : (
          <>
            <ListToolbar
              searchId="branches-search"
              searchLabel="Buscar por nombre o código"
              searchPlaceholder="Centro o código"
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
              <EmptyState title={list.hasActiveFilters ? "Sin coincidencias" : "Sin sucursales"}>
                <p>
                  {list.hasActiveFilters
                    ? "Ajuste la búsqueda o el filtro."
                    : "Aún no hay sucursales registradas para este gimnasio."}
                </p>
              </EmptyState>
            ) : (
              <>
                <BranchesGrid
                  branches={list.pageSlice}
                  memberCounts={{}}
                  showMemberCounts={false}
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
          </>
        )}
      </Card>

      <BranchDetailModal
        branch={detailBranch}
        memberCount={0}
        onClose={() => setDetailBranch(null)}
        statusLabel={detailBranch ? branchStatusLabel(detailBranch.status) : ""}
        statusVariant={detailBranch ? branchStatusBadgeVariant(detailBranch.status) : "demo"}
      />
    </div>
  );
}

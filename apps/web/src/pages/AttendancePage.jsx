import { useMemo, useState } from "react";
import DemoBranchScopeBanner from "../components/layout/DemoBranchScopeBanner.jsx";
import { useBranchScopedItems } from "../hooks/useBranchScopedItems.js";
import AttendanceDetailModal from "../components/attendance/AttendanceDetailModal.jsx";
import AttendanceRecordsTable, { ATTENDANCE_SORT } from "../components/attendance/AttendanceRecordsTable.jsx";
import AttendanceSummary from "../components/attendance/AttendanceSummary.jsx";
import Card from "../components/ui/Card.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ListToolbar from "../components/ui/ListToolbar.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Pagination from "../components/ui/Pagination.jsx";
import {
  ATTENDANCE_PAGE_SIZE_OPTIONS,
  ATTENDANCE_PERIOD_PRESETS,
  DEMO_ATTENDANCE_RECORDS,
  filterRecordsByPeriodPreset,
  summarizeAttendance,
} from "../demo/attendance-records.demo.js";
import { usePaginatedListState } from "../hooks/usePaginatedListState.js";

function filterRecord(item, { query }) {
  const q = query.trim().toLowerCase();
  if (!q) {
    return true;
  }
  return item.fullName.toLowerCase().includes(q) || item.memberCode.toLowerCase().includes(q);
}

function compareRecords(a, b, sortField, sortDir) {
  const da = `${a.dateIso}T${a.timeLocal}`;
  const db = `${b.dateIso}T${b.timeLocal}`;
  const cmp = da.localeCompare(db);
  return sortDir === "asc" ? cmp : -cmp;
}

const listOptions = {
  filterItem: filterRecord,
  compareItems: compareRecords,
  defaultSortField: ATTENDANCE_SORT.DATETIME,
  defaultSortDir: "desc",
  defaultPageSize: 10,
};

export default function AttendancePage() {
  const [detailRecord, setDetailRecord] = useState(null);
  const [periodPreset, setPeriodPreset] = useState("14");

  const periodRecords = useMemo(
    () => filterRecordsByPeriodPreset(DEMO_ATTENDANCE_RECORDS, periodPreset),
    [periodPreset],
  );

  const branchScopedRecords = useBranchScopedItems(periodRecords);
  const list = usePaginatedListState(branchScopedRecords, listOptions);

  function handlePeriodChange(value) {
    setPeriodPreset(value);
    list.setPage(1);
  }

  const filteredForSummary = useMemo(() => {
    return branchScopedRecords.filter((item) => filterRecord(item, { query: list.query }));
  }, [branchScopedRecords, list.query]);

  const summary = useMemo(() => summarizeAttendance(filteredForSummary), [filteredForSummary]);

  return (
    <div className="demo-module-page">
      <PageHeader
        title="Asistencias (demostración)"
        description="Historial de entradas ficticias por socio, fecha y sucursal demo. Sin QR, biometría ni validación de acceso real."
      />

      <DemoBranchScopeBanner />

      <Card title="Resumen y registros" className="demo-module-page__card">
        <ListToolbar
          searchId="attendance-search"
          searchLabel="Buscar por socio"
          searchPlaceholder="Nombre o código demo"
          query={list.query}
          onQueryChange={list.setQuery}
          filters={[
            {
              id: "attendance-filter-period",
              label: "Periodo",
              value: periodPreset,
              onChange: handlePeriodChange,
              options: ATTENDANCE_PERIOD_PRESETS,
            },
          ]}
          totalCount={list.totalCount}
          sortMobile={{
            groupLabel: "Ordenar",
            sortField: list.sortField,
            sortDir: list.sortDir,
            onSort: list.toggleSort,
            fields: [{ key: ATTENDANCE_SORT.DATETIME, label: "Fecha y hora" }],
          }}
        />

        <AttendanceSummary summary={summary} />

        {list.totalCount === 0 ? (
          <EmptyState title={list.hasActiveFilters ? "Sin coincidencias" : "Sin registros en el periodo"}>
            {list.hasActiveFilters ? (
              <p>Pruebe otro socio, cambie la sucursal en la barra superior o amplíe el periodo.</p>
            ) : (
              <p>No hay entradas ficticias para mostrar.</p>
            )}
          </EmptyState>
        ) : (
          <>
            <AttendanceRecordsTable
              rows={list.pageSlice}
              sortField={list.sortField}
              sortDir={list.sortDir}
              onSort={list.toggleSort}
              onViewDetail={setDetailRecord}
            />
            <Pagination
              page={list.page}
              pageCount={list.pageCount}
              pageSize={list.pageSize}
              pageSizeOptions={ATTENDANCE_PAGE_SIZE_OPTIONS}
              onPageChange={list.setPage}
              onPageSizeChange={list.setPageSize}
            />
          </>
        )}
      </Card>

      <AttendanceDetailModal record={detailRecord} onClose={() => setDetailRecord(null)} />
    </div>
  );
}

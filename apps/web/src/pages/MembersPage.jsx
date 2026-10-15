import { useState } from "react";
import MemberDetailModal from "../components/members/MemberDetailModal.jsx";
import MembersTable from "../components/members/MembersTable.jsx";
import MembersToolbar from "../components/members/MembersToolbar.jsx";
import NewMemberDemoModal from "../components/members/NewMemberDemoModal.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import Pagination from "../components/ui/Pagination.jsx";
import { DEMO_MEMBERS, MEMBERS_PAGE_SIZE_OPTIONS } from "../demo/members.demo.js";
import { useMemberListState } from "../hooks/useMemberListState.js";

export default function MembersPage() {
  const [members, setMembers] = useState(() => [...DEMO_MEMBERS]);
  const [sessionSeq, setSessionSeq] = useState(1);
  const [detailMember, setDetailMember] = useState(null);
  const [newOpen, setNewOpen] = useState(false);
  const [demoNotice, setDemoNotice] = useState(null);

  const list = useMemberListState(members);

  function handleCreated(member) {
    setMembers((prev) => [member, ...prev]);
    setSessionSeq((n) => n + 1);
    setDemoNotice({
      title: "Registro de demostración",
      message: `${member.fullName} (${member.memberCode}) se agregó solo en memoria para esta sesión.`,
    });
  }

  return (
    <div className="members-page">
      <PageHeader
        title="Socios (demostración)"
        description="Listado ficticio para explorar búsqueda, filtros, ordenamiento y altas locales. No hay conexión con MongoDB ni la API de socios."
      >
        <Button type="button" variant="primary" onClick={() => setNewOpen(true)}>
          Nuevo socio (Demo)
        </Button>
      </PageHeader>

      {demoNotice ? (
        <div className="members-page__notice" role="status">
          <p className="members-page__notice-title">{demoNotice.title}</p>
          <p className="members-page__notice-text">{demoNotice.message}</p>
          <Button type="button" variant="secondary" onClick={() => setDemoNotice(null)}>
            Entendido
          </Button>
        </div>
      ) : null}

      <Card title="Directorio de socios ficticios" className="members-page__card">
        <MembersToolbar
          query={list.query}
          onQueryChange={list.setQuery}
          statusFilter={list.statusFilter}
          onStatusFilterChange={list.setStatusFilter}
          membershipFilter={list.membershipFilter}
          onMembershipFilterChange={list.setMembershipFilter}
          totalCount={list.totalCount}
          sortField={list.sortField}
          sortDir={list.sortDir}
          onSort={list.toggleSort}
        />

        {list.totalCount === 0 ? (
          <EmptyState title={list.hasActiveFilters ? "Sin coincidencias" : "Sin socios de demostración"}>
            {list.hasActiveFilters ? (
              <p>Ajuste la búsqueda o los filtros para ver otros registros ficticios.</p>
            ) : (
              <p>No hay registros demo disponibles en esta vista.</p>
            )}
          </EmptyState>
        ) : (
          <>
            <MembersTable
              rows={list.pageSlice}
              sortField={list.sortField}
              sortDir={list.sortDir}
              onSort={list.toggleSort}
              onViewDetail={setDetailMember}
            />
            <Pagination
              page={list.page}
              pageCount={list.pageCount}
              pageSize={list.pageSize}
              pageSizeOptions={MEMBERS_PAGE_SIZE_OPTIONS}
              onPageChange={list.setPage}
              onPageSizeChange={list.setPageSize}
            />
          </>
        )}
      </Card>

      <MemberDetailModal member={detailMember} onClose={() => setDetailMember(null)} />
      <NewMemberDemoModal
        isOpen={newOpen}
        onClose={() => setNewOpen(false)}
        sessionIndex={sessionSeq}
        onCreated={handleCreated}
      />
    </div>
  );
}

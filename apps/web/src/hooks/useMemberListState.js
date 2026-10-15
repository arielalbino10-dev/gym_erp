import { useMemo, useState } from "react";

export const SORT_FIELDS = {
  NAME: "name",
  ENROLLED: "enrolledOn",
};

export function useMemberListState(members) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [membershipFilter, setMembershipFilter] = useState("");
  const [sortField, setSortField] = useState(SORT_FIELDS.NAME);
  const [sortDir, setSortDir] = useState("asc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return members.filter((member) => {
      if (statusFilter && member.status !== statusFilter) {
        return false;
      }
      if (membershipFilter && member.membershipType !== membershipFilter) {
        return false;
      }
      if (!q) {
        return true;
      }
      const inName = member.fullName.toLowerCase().includes(q);
      const inCode = member.memberCode.toLowerCase().includes(q);
      return inName || inCode;
    });
  }, [members, query, statusFilter, membershipFilter]);

  const sorted = useMemo(() => {
    const list = [...filtered];
    list.sort((a, b) => {
      let cmp = 0;
      if (sortField === SORT_FIELDS.NAME) {
        cmp = a.fullName.localeCompare(b.fullName, "es");
      } else {
        cmp = a.enrolledOn.localeCompare(b.enrolledOn);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [filtered, sortField, sortDir]);

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
      setSortDir(field === SORT_FIELDS.NAME ? "asc" : "desc");
    }
  }

  function updateQuery(value) {
    setQuery(value);
    setPage(1);
  }

  function updateStatusFilter(value) {
    setStatusFilter(value);
    setPage(1);
  }

  function updateMembershipFilter(value) {
    setMembershipFilter(value);
    setPage(1);
  }

  function updatePageSize(size) {
    setPageSize(size);
    setPage(1);
  }

  return {
    query,
    setQuery: updateQuery,
    statusFilter,
    setStatusFilter: updateStatusFilter,
    membershipFilter,
    setMembershipFilter: updateMembershipFilter,
    sortField,
    sortDir,
    toggleSort,
    page: safePage,
    setPage,
    pageSize,
    setPageSize: updatePageSize,
    totalCount: sorted.length,
    pageCount,
    pageSlice,
    hasActiveFilters: Boolean(query.trim() || statusFilter || membershipFilter),
  };
}

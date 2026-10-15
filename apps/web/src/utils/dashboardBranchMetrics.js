import { DEMO_ATTENDANCE_RECORDS } from "../demo/attendance-records.demo.js";
import { itemMatchesDemoBranch } from "../demo/branches.demo.js";
import { DEMO_MEMBERS, DEMO_REFERENCE_DATE, MEMBER_STATUS, MEMBERSHIP_TYPES } from "../demo/members.demo.js";
import { DEMO_ASSIGNED_MEMBERSHIPS, MEMBERSHIP_LIFECYCLE } from "../demo/memberships.demo.js";

function scopedMembers(branchId) {
  return DEMO_MEMBERS.filter((m) => itemMatchesDemoBranch(m, branchId));
}

function scopedAssignments(branchId) {
  return DEMO_ASSIGNED_MEMBERSHIPS.filter((a) => itemMatchesDemoBranch(a, branchId));
}

function scopedTodayAttendance(branchId) {
  return DEMO_ATTENDANCE_RECORDS.filter(
    (r) => r.dateIso === DEMO_REFERENCE_DATE && itemMatchesDemoBranch(r, branchId),
  );
}

export function computeDashboardMetricsForBranch(branchId) {
  const members = scopedMembers(branchId);
  const assignments = scopedAssignments(branchId);
  const todayRows = scopedTodayAttendance(branchId);

  const activeMembers = members.filter((m) => m.status === MEMBER_STATUS.ACTIVE).length;
  const vigentes = assignments.filter(
    (a) => a.lifecycle === MEMBERSHIP_LIFECYCLE.ACTIVE || a.lifecycle === MEMBERSHIP_LIFECYCLE.EXPIRING,
  ).length;

  const membershipByPlan = [
    { id: "plan-monthly", plan: "Mensual", membershipType: MEMBERSHIP_TYPES.MONTHLY },
    { id: "plan-quarterly", plan: "Trimestral", membershipType: MEMBERSHIP_TYPES.QUARTERLY },
    { id: "plan-annual", plan: "Anual", membershipType: MEMBERSHIP_TYPES.ANNUAL },
  ].map((row) => {
    const rows = assignments.filter((a) => a.membershipType === row.membershipType);
    const active = rows.filter(
      (a) => a.lifecycle === MEMBERSHIP_LIFECYCLE.ACTIVE || a.lifecycle === MEMBERSHIP_LIFECYCLE.EXPIRING,
    ).length;
    const expiringSoon = rows.filter((a) => a.lifecycle === MEMBERSHIP_LIFECYCLE.EXPIRING).length;
    return { ...row, active, expiringSoon };
  });

  return {
    activeMembers,
    vigentes,
    attendanceToday: todayRows.length,
    membershipByPlan,
    computedFromDemo: true,
  };
}

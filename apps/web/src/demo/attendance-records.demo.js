/**
 * Registros individuales de asistencia (check-in ficticio), coherentes con socios demo.
 */

import { DEMO_ATTENDANCE_DAILY_30 } from "./attendance.demo.js";
import { DEMO_BRANCHES, DEMO_MEMBERS, DEMO_REFERENCE_DATE, MEMBER_STATUS } from "./members.demo.js";

export { DEMO_REFERENCE_DATE };

const ACTIVE_DEMO_MEMBERS = DEMO_MEMBERS.filter((m) => m.status === MEMBER_STATUS.ACTIVE);

export const ATTENDANCE_PERIOD_PRESETS = [
  { value: "7", label: "Últimos 7 días" },
  { value: "14", label: "Últimos 14 días" },
  { value: "30", label: "Últimos 30 días" },
];

export const BRANCH_FILTER_OPTIONS = [
  { value: "", label: "Todas las sucursales demo" },
  ...DEMO_BRANCHES.map((name) => ({ value: name, label: name })),
];

const ENTRY_HOURS = [6, 7, 8, 9, 10, 11, 17, 18, 19, 20];

function padRecordId(index) {
  return `demo-att-${String(index).padStart(4, "0")}`;
}

function demoTimeForIndex(index) {
  const hour = ENTRY_HOURS[index % ENTRY_HOURS.length];
  const minute = (index * 7) % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function buildRecords() {
  const records = [];
  let seq = 1;
  DEMO_ATTENDANCE_DAILY_30.forEach((dayRow, dayIndex) => {
    const dateIso = dayRow.dateIso;
    const entriesThisDay = Math.min(16, Math.max(6, Math.round(dayRow.count / 8)));
    for (let j = 0; j < entriesThisDay; j += 1) {
      const member = ACTIVE_DEMO_MEMBERS[(dayIndex * 3 + j) % ACTIVE_DEMO_MEMBERS.length];
      records.push({
        recordId: padRecordId(seq),
        memberId: member.memberId,
        memberCode: member.memberCode,
        fullName: member.fullName,
        dateIso,
        timeLocal: demoTimeForIndex(seq),
        branchName: DEMO_BRANCHES[(dayIndex + j) % DEMO_BRANCHES.length],
        accessMethodLabel: "Registro manual (demo)",
        isDemo: true,
      });
      seq += 1;
    }
  });
  return records.sort((a, b) => {
    const da = `${a.dateIso}T${a.timeLocal}`;
    const db = `${b.dateIso}T${b.timeLocal}`;
    return db.localeCompare(da);
  });
}

export const DEMO_ATTENDANCE_RECORDS = buildRecords();

export const ATTENDANCE_PAGE_SIZE_OPTIONS = [5, 10, 25];

export function summarizeAttendance(records) {
  const uniqueMembers = new Set(records.map((r) => r.memberId));
  const byBranch = records.reduce((acc, row) => {
    acc[row.branchName] = (acc[row.branchName] || 0) + 1;
    return acc;
  }, {});
  const dates = records.map((r) => r.dateIso);
  const periodFrom = dates.length ? dates.reduce((a, b) => (a < b ? a : b)) : null;
  const periodTo = dates.length ? dates.reduce((a, b) => (a > b ? a : b)) : null;
  return {
    totalEntries: records.length,
    uniqueMembers: uniqueMembers.size,
    periodFrom,
    periodTo,
    byBranch,
  };
}

export function filterRecordsByPeriodPreset(records, presetDays) {
  const days = Number(presetDays) || 14;
  const allowed = new Set(DEMO_ATTENDANCE_DAILY_30.slice(-days).map((d) => d.dateIso));
  return records.filter((r) => allowed.has(r.dateIso));
}

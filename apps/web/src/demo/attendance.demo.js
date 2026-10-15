/** Serie diaria de asistencias — determinista, solo UI demo. */

/** Último día de la serie demo (no fechas futuras respecto al escenario UI-01.3). */
const SERIES_END_ISO = "2026-10-15";

function parseEndUtc() {
  const [y, m, d] = SERIES_END_ISO.split("-").map(Number);
  return Date.UTC(y, m - 1, d, 12, 0, 0);
}

function formatDayLabel(dateUtc) {
  return new Intl.DateTimeFormat("es-MX", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(dateUtc));
}

function formatFullDate(dateUtc) {
  return new Intl.DateTimeFormat("es-MX", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(dateUtc));
}

function demoCountForDayIndex(index) {
  return 98 + (index % 7) * 6 + (index % 5) * 3 + (index % 3);
}

/** 30 días consecutivos terminando en SERIES_END_ISO (valores fijos). */
export const DEMO_ATTENDANCE_DAILY_30 = Array.from({ length: 30 }, (_, index) => {
  const dayUtc = parseEndUtc() - (29 - index) * 86400000;
  const iso = new Date(dayUtc).toISOString().slice(0, 10);
  return {
    dateIso: iso,
    count: demoCountForDayIndex(index),
    labelShort: formatDayLabel(dayUtc),
    labelLong: formatFullDate(dayUtc),
  };
});

/**
 * @param {7 | 14 | 30} dayCount
 */
export function getAttendanceSeries(dayCount) {
  return DEMO_ATTENDANCE_DAILY_30.slice(-dayCount);
}

export const ATTENDANCE_PERIOD_OPTIONS = [
  { value: 7, label: "7 días" },
  { value: 14, label: "14 días" },
  { value: 30, label: "30 días" },
];

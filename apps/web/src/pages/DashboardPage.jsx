import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import DemoBranchScopeBanner from "../components/layout/DemoBranchScopeBanner.jsx";
import { useDemoUiPreferences } from "../app/providers/DemoUiPreferencesProvider.jsx";
import HealthIndicator from "../components/layout/HealthIndicator.jsx";
import BarChart from "../components/ui/BarChart.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import MetricCard from "../components/ui/MetricCard.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import { itemMatchesDemoBranch } from "../demo/branches.demo.js";
import { ATTENDANCE_PERIOD_OPTIONS, getAttendanceSeries } from "../demo/attendance.demo.js";
import {
  DEMO_DASHBOARD_LOAD_MS,
  DEMO_KPI_METRICS,
  DEMO_MEMBERSHIP_SUMMARY,
  DEMO_QUICK_ACTIONS,
  DEMO_RECENT_ACTIVITY,
} from "../demo/dashboard.demo.js";
import { computeDashboardMetricsForBranch } from "../utils/dashboardBranchMetrics.js";

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState(7);
  const { selectedBranchId, isBranchFilterActive } = useDemoUiPreferences();

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      if (!cancelled) {
        setLoading(false);
      }
    }, DEMO_DASHBOARD_LOAD_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  const series = useMemo(() => getAttendanceSeries(periodDays), [periodDays]);

  const branchMetrics = useMemo(
    () => (isBranchFilterActive ? computeDashboardMetricsForBranch(selectedBranchId) : null),
    [isBranchFilterActive, selectedBranchId],
  );

  const kpiRows = useMemo(() => {
    if (!branchMetrics) {
      return DEMO_KPI_METRICS;
    }
    return [
      {
        id: "active-members",
        title: "Socios activos",
        value: String(branchMetrics.activeMembers),
        footnote: "Calculado desde socios demo filtrados",
      },
      {
        id: "active-memberships",
        title: "Membresías vigentes",
        value: String(branchMetrics.vigentes),
        footnote: "Asignaciones vigentes o por vencer (demo)",
      },
      {
        id: "attendance-today",
        title: "Asistencias de hoy",
        value: String(branchMetrics.attendanceToday),
        footnote: "Registros demo del 2026-10-15 en la sucursal",
      },
      {
        id: "revenue-month",
        title: "Ingresos del mes",
        value: "$12,450",
        footnote: "Ilustrativo · no desglosado por sucursal",
      },
    ];
  }, [branchMetrics]);

  const activityItems = useMemo(
    () => DEMO_RECENT_ACTIVITY.filter((item) => itemMatchesDemoBranch(item, selectedBranchId)),
    [selectedBranchId],
  );

  const membershipSummary = useMemo(() => {
    if (!branchMetrics) {
      return DEMO_MEMBERSHIP_SUMMARY;
    }
    return branchMetrics.membershipByPlan;
  }, [branchMetrics]);

  return (
    <div className="dashboard">
      <PageHeader
        title="Resumen operativo (demostración)"
        description="Indicadores y gráficos con datos ficticios. No representan socios, pagos ni asistencias reales del gimnasio."
      />

      <DemoBranchScopeBanner />

      <div className="dashboard__kpi-grid">
        {kpiRows.map((metric) => (
          <MetricCard
            key={metric.id}
            title={metric.title}
            value={metric.value}
            footnote={metric.footnote}
            loading={loading}
          />
        ))}
      </div>

      <div className="dashboard__grid-two">
        <Card title="Asistencias por día" className="dashboard__chart-card">
          {isBranchFilterActive ? (
            <p className="dashboard__chart-scope-note" role="note">
              Gráfico agregado del escenario demo · no filtrado por sucursal (ilustrativo).
            </p>
          ) : null}
          <div className="dashboard__period-toolbar" role="group" aria-label="Periodo del gráfico">
            {ATTENDANCE_PERIOD_OPTIONS.map((opt) => (
              <Button
                key={opt.value}
                variant={periodDays === opt.value ? "primary" : "secondary"}
                pressed={periodDays === opt.value}
                onClick={() => setPeriodDays(opt.value)}
              >
                Últimos {opt.label}
              </Button>
            ))}
          </div>
          {loading ? (
            <div className="dashboard__chart-skeleton" aria-busy="true" aria-label="Cargando gráfico" />
          ) : (
            <BarChart data={series} title={`Asistencias — últimos ${periodDays} días (demo)`} />
          )}
        </Card>

        <Card title="Actividad reciente" className="dashboard__activity-card">
          {loading ? (
            <ul className="activity-list activity-list--loading" aria-busy="true">
              {[1, 2, 3, 4].map((i) => (
                <li key={i} className="activity-list__skeleton" />
              ))}
            </ul>
          ) : activityItems.length === 0 ? (
            <EmptyState title="Sin actividad demo en esta sucursal">
              Cambie el selector global o muestre todas las sucursales.
            </EmptyState>
          ) : (
            <ul className="activity-list">
              {activityItems.map((item) => (
                <li key={item.id} className="activity-list__item">
                  <time className="activity-list__time" dateTime={item.dateIso}>
                    {item.time}
                  </time>
                  <span className="activity-list__text">{item.text}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="dashboard__grid-two">
        <Card title="Membresías por plan">
          {loading ? (
            <div className="membership-summary membership-summary--loading" aria-busy="true" />
          ) : (
            <ul className="membership-summary">
              {membershipSummary.map((row) => (
                <li key={row.id} className="membership-summary__row">
                  <span className="membership-summary__plan">{row.plan}</span>
                  <span className="membership-summary__stat">
                    <strong>{row.active}</strong> vigentes
                  </span>
                  <span className="membership-summary__meta">
                    {row.expiringSoon > 0
                      ? `${row.expiringSoon} por vencer (demo)`
                      : "Sin vencimientos demo"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Acciones rápidas">
          <p className="dashboard__quick-intro">Solo navegación — no guarda datos.</p>
          <ul className="quick-actions">
            {DEMO_QUICK_ACTIONS.map((action) => (
              <li key={action.id}>
                <Link className="quick-actions__link" to={action.to}>
                  <span className="quick-actions__label">{action.label}</span>
                  <span className="quick-actions__desc">{action.description}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <p className="dashboard__infra-note">
        <span className="dashboard__infra-label">Infraestructura (health):</span>{" "}
        <HealthIndicator /> —{" "}
        <Link to="/configuracion">Ver diagnóstico en Configuración</Link>. No indica disponibilidad
        de módulos de negocio.
      </p>
    </div>
  );
}

import { Link } from "react-router-dom";
import Button from "../ui/Button.jsx";
import Card from "../ui/Card.jsx";
import { useDemoUiPreferences } from "../../app/providers/DemoUiPreferencesProvider.jsx";
import { demoBranchSelectOptions } from "../../demo/branches.demo.js";

export default function DemoPreferencesSection() {
  const {
    selectedBranchId,
    setSelectedBranchId,
    compactLayout,
    setCompactLayout,
    showBranchScopeBanner,
    setShowBranchScopeBanner,
    resetVisualPrefs,
  } = useDemoUiPreferences();

  const branchOptions = demoBranchSelectOptions();

  return (
    <Card title="Preferencias visuales (demostración)">
      <p className="settings-section__intro">
        Cambios locales en esta sesión del navegador. No se envían al servidor ni se guardan como
        configuración operativa de la empresa.
      </p>
      <fieldset className="settings-fieldset">
        <legend className="settings-fieldset__legend">Sucursal demo en la barra superior</legend>
        <label className="settings-fieldset__label" htmlFor="settings-demo-branch">
          Filtro visual global
        </label>
        <select
          id="settings-demo-branch"
          className="ui-select settings-fieldset__control"
          value={selectedBranchId}
          onChange={(e) => setSelectedBranchId(e.target.value)}
        >
          {branchOptions.map((opt) => (
            <option key={opt.value || "all"} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <p className="settings-fieldset__hint">No sustituye permisos reales por sucursal (ADR-0003).</p>
      </fieldset>
      <fieldset className="settings-fieldset">
        <legend className="settings-fieldset__legend">Presentación</legend>
        <div className="settings-check">
          <input
            id="pref-compact-layout"
            type="checkbox"
            checked={compactLayout}
            onChange={(e) => setCompactLayout(e.target.checked)}
          />
          <label htmlFor="pref-compact-layout">Vista compacta (menos espaciado en contenido)</label>
        </div>
        <div className="settings-check">
          <input
            id="pref-branch-banner"
            type="checkbox"
            checked={showBranchScopeBanner}
            onChange={(e) => setShowBranchScopeBanner(e.target.checked)}
          />
          <label htmlFor="pref-branch-banner">Mostrar aviso cuando una sucursal demo esté filtrada</label>
        </div>
      </fieldset>
      <div className="settings-section__actions">
        <Button type="button" variant="secondary" onClick={resetVisualPrefs}>
          Restablecer preferencias demo
        </Button>
        <Link to="/sucursales" className="ui-btn ui-btn--secondary">
          Ver catálogo de sucursales
        </Link>
      </div>
    </Card>
  );
}

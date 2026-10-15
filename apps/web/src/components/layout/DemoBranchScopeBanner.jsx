import { Link } from "react-router-dom";
import { useDemoUiPreferences } from "../../app/providers/DemoUiPreferencesProvider.jsx";

export default function DemoBranchScopeBanner() {
  const { selectedBranch, isBranchFilterActive, showBranchScopeBanner } = useDemoUiPreferences();

  if (!showBranchScopeBanner || !isBranchFilterActive || !selectedBranch) {
    return null;
  }

  return (
    <p className="demo-branch-scope-banner" role="status">
      Vista filtrada por sucursal demo: <strong>{selectedBranch.name}</strong> ({selectedBranch.branchCode}).{" "}
      <Link to="/sucursales">Ver catálogo de sucursales</Link>
    </p>
  );
}

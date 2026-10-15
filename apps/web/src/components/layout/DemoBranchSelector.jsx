import SelectInput from "../ui/SelectInput.jsx";
import { demoBranchSelectOptions } from "../../demo/branches.demo.js";
import { useDemoUiPreferences } from "../../app/providers/DemoUiPreferencesProvider.jsx";

export default function DemoBranchSelector() {
  const { selectedBranchId, setSelectedBranchId } = useDemoUiPreferences();
  const options = demoBranchSelectOptions();

  return (
    <div className="demo-branch-selector">
      <label className="demo-branch-selector__label" htmlFor="demo-global-branch">
        Sucursal demo
      </label>
      <SelectInput
        id="demo-global-branch"
        className="demo-branch-selector__select"
        value={selectedBranchId}
        onChange={(e) => setSelectedBranchId(e.target.value)}
        options={options}
        aria-describedby="demo-global-branch-hint"
      />
      <span id="demo-global-branch-hint" className="demo-branch-selector__hint">
        Filtro visual · no es permiso
      </span>
    </div>
  );
}

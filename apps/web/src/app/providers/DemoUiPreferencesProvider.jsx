import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { DEMO_BRANCH_ALL, getDemoBranchById } from "../../demo/branches.demo.js";

const DEFAULT_VISUAL_PREFS = {
  compactLayout: false,
  showBranchScopeBanner: true,
};

const DemoUiPreferencesContext = createContext(null);

export function DemoUiPreferencesProvider({ children }) {
  const [selectedBranchId, setSelectedBranchId] = useState(DEMO_BRANCH_ALL);
  const [visualPrefs, setVisualPrefs] = useState(DEFAULT_VISUAL_PREFS);

  const setCompactLayout = useCallback((compactLayout) => {
    setVisualPrefs((prev) => ({ ...prev, compactLayout }));
  }, []);

  const setShowBranchScopeBanner = useCallback((showBranchScopeBanner) => {
    setVisualPrefs((prev) => ({ ...prev, showBranchScopeBanner }));
  }, []);

  const resetVisualPrefs = useCallback(() => {
    setVisualPrefs(DEFAULT_VISUAL_PREFS);
  }, []);

  const value = useMemo(() => {
    const selectedBranch = selectedBranchId ? getDemoBranchById(selectedBranchId) : null;
    return {
      selectedBranchId,
      selectedBranch,
      setSelectedBranchId,
      isBranchFilterActive: Boolean(selectedBranchId),
      compactLayout: visualPrefs.compactLayout,
      showBranchScopeBanner: visualPrefs.showBranchScopeBanner,
      setCompactLayout,
      setShowBranchScopeBanner,
      resetVisualPrefs,
    };
  }, [
    selectedBranchId,
    visualPrefs,
    setCompactLayout,
    setShowBranchScopeBanner,
    resetVisualPrefs,
  ]);

  return <DemoUiPreferencesContext.Provider value={value}>{children}</DemoUiPreferencesContext.Provider>;
}

export function useDemoUiPreferences() {
  const ctx = useContext(DemoUiPreferencesContext);
  if (!ctx) {
    throw new Error("useDemoUiPreferences debe usarse dentro de DemoUiPreferencesProvider");
  }
  return ctx;
}

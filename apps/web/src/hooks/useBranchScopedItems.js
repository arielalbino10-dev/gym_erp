import { useMemo } from "react";
import { itemMatchesDemoBranch } from "../demo/branches.demo.js";
import { useDemoUiPreferences } from "../app/providers/DemoUiPreferencesProvider.jsx";

export function useBranchScopedItems(items) {
  const { selectedBranchId } = useDemoUiPreferences();
  return useMemo(
    () => items.filter((item) => itemMatchesDemoBranch(item, selectedBranchId)),
    [items, selectedBranchId],
  );
}

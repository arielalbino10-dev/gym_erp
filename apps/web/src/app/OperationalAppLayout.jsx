import { Outlet } from "react-router-dom";
import { ApiHealthProvider } from "./providers/ApiHealthProvider.jsx";
import { DemoUiPreferencesProvider } from "./providers/DemoUiPreferencesProvider.jsx";

/** Health check y preferencias demo solo dentro del ERP autenticado. */
export default function OperationalAppLayout() {
  return (
    <ApiHealthProvider>
      <DemoUiPreferencesProvider>
        <Outlet />
      </DemoUiPreferencesProvider>
    </ApiHealthProvider>
  );
}

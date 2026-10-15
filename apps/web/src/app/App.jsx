import { RouterProvider } from "react-router-dom";
import { ApiHealthProvider } from "./providers/ApiHealthProvider.jsx";
import { DemoUiPreferencesProvider } from "./providers/DemoUiPreferencesProvider.jsx";
import { router } from "./routes.jsx";

export default function App() {
  return (
    <ApiHealthProvider>
      <DemoUiPreferencesProvider>
        <RouterProvider router={router} />
      </DemoUiPreferencesProvider>
    </ApiHealthProvider>
  );
}

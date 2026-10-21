import { RouterProvider } from "react-router-dom";
import { ApiHealthProvider } from "./providers/ApiHealthProvider.jsx";
import { DemoUiPreferencesProvider } from "./providers/DemoUiPreferencesProvider.jsx";
import { GymAuthProvider } from "./providers/GymAuthProvider.jsx";
import { router } from "./routes.jsx";

export default function App() {
  return (
    <ApiHealthProvider>
      <GymAuthProvider>
        <DemoUiPreferencesProvider>
          <RouterProvider router={router} />
        </DemoUiPreferencesProvider>
      </GymAuthProvider>
    </ApiHealthProvider>
  );
}

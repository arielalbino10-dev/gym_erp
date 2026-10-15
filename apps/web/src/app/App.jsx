import { RouterProvider } from "react-router-dom";
import { ApiHealthProvider } from "./providers/ApiHealthProvider.jsx";
import { router } from "./routes.jsx";

export default function App() {
  return (
    <ApiHealthProvider>
      <RouterProvider router={router} />
    </ApiHealthProvider>
  );
}

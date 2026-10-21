import { Outlet } from "react-router-dom";
import { GymAuthProvider } from "./providers/GymAuthProvider.jsx";

/** Monta autenticación gym solo en login y rutas operativas (no en la landing). */
export default function GymAuthLayout() {
  return (
    <GymAuthProvider>
      <Outlet />
    </GymAuthProvider>
  );
}

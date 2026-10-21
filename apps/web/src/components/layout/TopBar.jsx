import { useLocation } from "react-router-dom";
import { titleForPathname } from "../../app/navigation.js";
import { Link } from "react-router-dom";
import { useGymAuth } from "../../app/providers/GymAuthProvider.jsx";
import DemoBranchSelector from "./DemoBranchSelector.jsx";
import HealthIndicator from "./HealthIndicator.jsx";
import Button from "../ui/Button.jsx";

export default function TopBar() {
  const { pathname } = useLocation();
  const title = titleForPathname(pathname);
  const { session, logout, busy } = useGymAuth();

  return (
    <header className="topbar">
      <div className="topbar__titles">
        <p className="topbar__eyebrow">
          {session?.tenant_display_name ? session.tenant_display_name : "Gym ERP"}
        </p>
        <h1 className="topbar__title">{title}</h1>
      </div>
      <div className="topbar__actions">
        <DemoBranchSelector />
        <HealthIndicator />
        <Link to="/seleccionar-gimnasio" className="topbar__link">
          Cambiar gimnasio
        </Link>
        <Button type="button" variant="secondary" disabled={busy} onClick={() => logout()}>
          Salir
        </Button>
      </div>
    </header>
  );
}

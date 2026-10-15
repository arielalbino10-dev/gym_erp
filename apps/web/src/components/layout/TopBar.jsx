import { useLocation } from "react-router-dom";
import { titleForPathname } from "../../app/navigation.js";
import DemoBranchSelector from "./DemoBranchSelector.jsx";
import HealthIndicator from "./HealthIndicator.jsx";

export default function TopBar() {
  const { pathname } = useLocation();
  const title = titleForPathname(pathname);

  return (
    <header className="topbar">
      <div className="topbar__titles">
        <p className="topbar__eyebrow">Gym ERP</p>
        <h1 className="topbar__title">{title}</h1>
      </div>
      <div className="topbar__actions">
        <DemoBranchSelector />
        <HealthIndicator />
      </div>
    </header>
  );
}

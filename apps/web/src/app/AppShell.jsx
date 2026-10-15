import { useEffect, useRef } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { titleForPathname } from "./navigation.js";
import DemoBanner from "../components/layout/DemoBanner.jsx";
import MobileNav from "../components/layout/MobileNav.jsx";
import Sidebar from "../components/layout/Sidebar.jsx";
import SkipLink from "../components/layout/SkipLink.jsx";
import TopBar from "../components/layout/TopBar.jsx";
import { useDemoUiPreferences } from "./providers/DemoUiPreferencesProvider.jsx";

export default function AppShell() {
  const { compactLayout } = useDemoUiPreferences();
  const { pathname } = useLocation();
  const mainRef = useRef(null);
  const isFirstRouteEffect = useRef(true);

  useEffect(() => {
    const section = titleForPathname(pathname);
    document.title = section === "Dashboard" ? "Gym ERP" : `${section} · Gym ERP`;
    if (isFirstRouteEffect.current) {
      isFirstRouteEffect.current = false;
      return;
    }
    mainRef.current?.focus({ preventScroll: true });
  }, [pathname]);

  return (
    <div className="app">
      <SkipLink />
      <DemoBanner />
      <div className="app__frame">
        <Sidebar />
        <div className="app__content-column">
          <TopBar />
          <main
            id="main-content"
            ref={mainRef}
            className={`app__main${compactLayout ? " app__main--compact" : ""}`}
            tabIndex={-1}
          >
            <Outlet />
          </main>
        </div>
      </div>
      <MobileNav />
    </div>
  );
}

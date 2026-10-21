import { useCallback, useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import { landingSectionHash, ROUTE_PATHS } from "../../app/routePaths.js";
import { LANDING_NAV } from "../../landing/landingContent.js";
import Button from "../ui/Button.jsx";

export default function PublicHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuId = useId();

  const closeMenu = useCallback(() => setMenuOpen(false), []);

  useEffect(() => {
    if (!menuOpen) {
      return undefined;
    }
    function onKeyDown(event) {
      if (event.key === "Escape") {
        closeMenu();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [menuOpen, closeMenu]);

  useEffect(() => {
    document.body.classList.toggle("landing-nav-open", menuOpen);
    return () => document.body.classList.remove("landing-nav-open");
  }, [menuOpen]);

  return (
    <header className="landing-header">
      <div className="landing-header__inner">
        <Link className="landing-brand" to={ROUTE_PATHS.landing}>
          <span className="landing-brand__mark" aria-hidden="true">
            G
          </span>
          <span className="landing-brand__text">Gym ERP</span>
        </Link>

        <nav className="landing-header__nav" aria-label="Secciones principales">
          <ul className="landing-header__nav-list">
            {LANDING_NAV.map((item) => (
              <li key={item.sectionId}>
                <a href={landingSectionHash(item.sectionId)}>{item.label}</a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="landing-header__actions">
          <Link className="landing-header__login-btn" to={ROUTE_PATHS.login}>
            Iniciar sesión
          </Link>
          <Button
            type="button"
            className="landing-header__menu-btn"
            variant="secondary"
            aria-expanded={menuOpen}
            aria-controls={menuId}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? "Cerrar menú" : "Menú"}
          </Button>
        </div>
      </div>

      <nav
        id={menuId}
        className={`landing-mobile-nav ${menuOpen ? "landing-mobile-nav--open" : ""}`}
        aria-label="Menú móvil"
        hidden={!menuOpen}
      >
        <ul className="landing-mobile-nav__list">
          {LANDING_NAV.map((item) => (
            <li key={item.sectionId}>
              <a href={landingSectionHash(item.sectionId)} onClick={closeMenu}>
                {item.label}
              </a>
            </li>
          ))}
          <li>
            <Link to={ROUTE_PATHS.login} onClick={closeMenu}>
              Iniciar sesión
            </Link>
          </li>
        </ul>
      </nav>
    </header>
  );
}

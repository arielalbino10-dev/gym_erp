import { NavLink } from "react-router-dom";
import { NAV_ITEMS } from "../../app/navigation.js";

export default function MobileNav() {
  return (
    <nav className="mobile-nav" aria-label="Navegación móvil">
      <ul className="mobile-nav__list">
        {NAV_ITEMS.map((item) => (
          <li key={item.to} className="mobile-nav__item">
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                isActive ? "mobile-nav__link mobile-nav__link--active" : "mobile-nav__link"
              }
            >
              <span className="mobile-nav__label">{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

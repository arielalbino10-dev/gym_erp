import { NavLink } from "react-router-dom";
import { NAV_ITEMS } from "../../app/navigation.js";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo" aria-hidden>
          GE
        </span>
        <div>
          <p className="sidebar__product">Gym ERP</p>
          <p className="sidebar__eyebrow">Administración · México</p>
        </div>
      </div>
      <nav className="sidebar__nav" aria-label="Navegación principal">
        <ul className="sidebar__list">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}

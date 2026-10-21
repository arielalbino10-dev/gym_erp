import Badge from "../ui/Badge.jsx";

const ROWS = [
  { name: "Sucursal Centro", code: "CTR-01", city: "Zona metropolitana", status: "Activa" },
  { name: "Sucursal Norte", code: "NTE-02", city: "Corredor norte", status: "Activa" },
  { name: "Sucursal Sur", code: "SUR-03", city: "Expansión", status: "En apertura" },
];

/** Vista ampliada del módulo de sucursales (composición distinta al hero). */
export default function ProductPreviewShowcase() {
  return (
    <figure className="landing-showcase">
      <div className="landing-showcase__frame" aria-hidden="true">
        <header className="landing-showcase__topbar">
          <span>Gym ERP</span>
          <span className="landing-showcase__tenant">Tenant · Vista demostrativa</span>
        </header>
        <div className="landing-showcase__layout">
          <aside className="landing-showcase__aside">
            <p className="landing-showcase__aside-title">Operación</p>
            <span className="landing-showcase__nav landing-showcase__nav--active">Sucursales</span>
            <span className="landing-showcase__nav">Socios</span>
            <span className="landing-showcase__nav">Membresías</span>
            <span className="landing-showcase__nav">Asistencias</span>
          </aside>
          <div className="landing-showcase__content">
            <div className="landing-showcase__toolbar">
              <h3 className="landing-showcase__heading">Sucursales</h3>
              <span className="landing-showcase__pill">Datos ilustrativos</span>
            </div>
            <table className="landing-showcase__table">
              <thead>
                <tr>
                  <th scope="col">Nombre</th>
                  <th scope="col">Código</th>
                  <th scope="col">Zona</th>
                  <th scope="col">Estado</th>
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => (
                  <tr key={row.code}>
                    <td>{row.name}</td>
                    <td>{row.code}</td>
                    <td>{row.city}</td>
                    <td>
                      <Badge variant={row.status === "Activa" ? "success" : "warning"}>
                        {row.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <figcaption className="landing-showcase__caption">
        Vista demostrativa del ERP — no representa clientes ni datos reales.
      </figcaption>
    </figure>
  );
}

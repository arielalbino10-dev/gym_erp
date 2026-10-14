import { useEffect, useState } from "react";
import { fetchHealthReady } from "./api/client.js";

const STATUS = {
  loading: "loading",
  ready: "ready",
  notReady: "not_ready",
  error: "error",
};

export default function App() {
  const [status, setStatus] = useState(STATUS.loading);
  const [detail, setDetail] = useState("Comprobando API…");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const result = await fetchHealthReady();
        if (cancelled) return;
        if (result.ok && result.body?.status === "ready") {
          setStatus(STATUS.ready);
          setDetail("La API responde y MongoDB está disponible.");
        } else if (result.ok === false && result.status === 503) {
          setStatus(STATUS.notReady);
          setDetail(
            "La API responde, pero MongoDB no está listo (503). Configure MONGODB_URI con un usuario de aplicación.",
          );
        } else {
          setStatus(STATUS.error);
          setDetail(`Respuesta inesperada (${result.status}).`);
        }
      } catch {
        if (!cancelled) {
          setStatus(STATUS.error);
          setDetail(
            "No se pudo conectar con la API. ¿Está uvicorn en http://127.0.0.1:8000?",
          );
        }
      }
    }

    check();
    return () => {
      cancelled = true;
    };
  }, []);

  const badgeClass =
    status === STATUS.ready
      ? "badge badge--ok"
      : status === STATUS.loading
        ? "badge badge--loading"
        : "badge badge--warn";

  const badgeLabel =
    status === STATUS.ready
      ? "Operativo"
      : status === STATUS.loading
        ? "Comprobando…"
        : status === STATUS.notReady
          ? "API sin MongoDB"
          : "Sin conexión";

  return (
    <div className="page">
      <header className="header">
        <p className="eyebrow">Administración · México</p>
        <h1>Gym ERP</h1>
        <p className="subtitle">ERP SaaS para gimnasios — Release 0.1 (fundación H0-B)</p>
      </header>

      <main className="card">
        <h2>Estado del sistema</h2>
        <p className={`${badgeClass}`}>{badgeLabel}</p>
        <p className="detail">{detail}</p>
        <p className="hint">
          Endpoint: <code>GET /api/v1/health/ready</code>
        </p>
      </main>

      <footer className="footer">
        <small>JavaScript (.jsx) · React + Vite · FastAPI</small>
      </footer>
    </div>
  );
}

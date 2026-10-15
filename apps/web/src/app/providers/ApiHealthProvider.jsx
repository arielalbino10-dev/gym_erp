import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { fetchHealthReady } from "../../api/client.js";

export const HEALTH_STATUS = {
  loading: "loading",
  ready: "ready",
  notReady: "not_ready",
  error: "error",
};

const ApiHealthContext = createContext(null);

export function ApiHealthProvider({ children }) {
  const [status, setStatus] = useState(HEALTH_STATUS.loading);
  const [detail, setDetail] = useState("Comprobando API…");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      const dev = import.meta.env.DEV;
      try {
        const result = await fetchHealthReady();
        if (cancelled) return;
        if (result.ok && result.body?.status === "ready") {
          setStatus(HEALTH_STATUS.ready);
          setDetail(
            dev
              ? "La API responde y MongoDB está disponible."
              : "Servicio de infraestructura disponible.",
          );
        } else if (result.ok === false && result.status === 503) {
          setStatus(HEALTH_STATUS.notReady);
          setDetail(
            dev
              ? "La API responde, pero MongoDB no está listo (503). Revise MONGODB_URI en el servidor."
              : "Servicio temporalmente no disponible (503).",
          );
        } else {
          setStatus(HEALTH_STATUS.error);
          setDetail(
            dev
              ? `Respuesta inesperada del health check (${result.status}).`
              : "No se pudo verificar la infraestructura.",
          );
        }
      } catch (error) {
        if (!cancelled) {
          setStatus(HEALTH_STATUS.error);
          const timedOut = error instanceof DOMException && error.name === "TimeoutError";
          if (timedOut) {
            setDetail(
              dev
                ? "Tiempo de espera agotado al consultar /health/ready."
                : "Tiempo de espera agotado al verificar el servicio.",
            );
          } else {
            setDetail(
              dev
                ? "No se pudo conectar con la API. ¿Está uvicorn en http://127.0.0.1:8000?"
                : "No se pudo conectar con el servicio de infraestructura.",
            );
          }
        }
      }
    }

    check();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      status,
      detail,
      badgeLabel:
        status === HEALTH_STATUS.ready
          ? "API en línea"
          : status === HEALTH_STATUS.loading
            ? "Comprobando…"
            : status === HEALTH_STATUS.notReady
              ? "API sin MongoDB"
              : "Sin conexión",
    }),
    [status, detail],
  );

  return <ApiHealthContext.Provider value={value}>{children}</ApiHealthContext.Provider>;
}

export function useApiHealth() {
  const ctx = useContext(ApiHealthContext);
  if (!ctx) {
    throw new Error("useApiHealth debe usarse dentro de ApiHealthProvider.");
  }
  return ctx;
}

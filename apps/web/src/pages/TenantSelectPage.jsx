import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGymAuth } from "../app/providers/GymAuthProvider.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";

export default function TenantSelectPage() {
  const { memberships, loadMemberships, chooseTenant, busy, error, logout, hasActiveTenant } =
    useGymAuth();
  const [loadingList, setLoadingList] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    if (hasActiveTenant) {
      navigate("/sucursales", { replace: true });
    }
  }, [hasActiveTenant, navigate]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadMemberships();
      } finally {
        if (!cancelled) {
          setLoadingList(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadMemberships]);

  async function handleSelect(tenantId) {
    await chooseTenant(tenantId);
    navigate("/sucursales", { replace: true });
  }

  return (
    <div className="auth-page">
      <Card title="Seleccionar gimnasio" className="auth-page__card">
        <p className="auth-page__hint">
          Elija el gimnasio con el que operará en esta sesión. Solo se muestran membresías activas
          autorizadas por el servidor.
        </p>
        {loadingList ? (
          <p>Cargando gimnasios…</p>
        ) : memberships.length === 0 ? (
          <EmptyState title="Sin gimnasios disponibles">
            <p>No hay membresías activas para esta identidad.</p>
            <Button type="button" variant="secondary" onClick={() => logout()}>
              Cerrar sesión
            </Button>
          </EmptyState>
        ) : (
          <ul className="tenant-select-list">
            {memberships.map((row) => (
              <li key={row.tenant_id}>
                <Button
                  type="button"
                  disabled={busy}
                  onClick={() => handleSelect(row.tenant_id)}
                  aria-label={`Seleccionar ${row.display_name}`}
                >
                  {row.display_name}
                </Button>
              </li>
            ))}
          </ul>
        )}
        {error ? (
          <p className="auth-form__error" role="alert">
            {error}
          </p>
        ) : null}
      </Card>
    </div>
  );
}

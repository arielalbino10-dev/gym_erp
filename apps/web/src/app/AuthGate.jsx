import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useGymAuth } from "./providers/GymAuthProvider.jsx";

export function PublicOnlyRoute() {
  const { isAuthenticated, bootstrapping, hasActiveTenant } = useGymAuth();
  const location = useLocation();

  if (bootstrapping) {
    return <p className="auth-loading">Comprobando sesión…</p>;
  }
  if (isAuthenticated && hasActiveTenant) {
    const redirect = location.state?.from?.pathname || "/sucursales";
    return <Navigate to={redirect} replace />;
  }
  if (isAuthenticated) {
    return <Navigate to="/seleccionar-gimnasio" replace />;
  }
  return <Outlet />;
}

export function RequireGymAuth() {
  const { isAuthenticated, bootstrapping } = useGymAuth();
  const location = useLocation();

  if (bootstrapping) {
    return <p className="auth-loading">Comprobando sesión…</p>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

export function RequireActiveTenant() {
  const { hasActiveTenant, bootstrapping, isAuthenticated } = useGymAuth();
  const location = useLocation();

  if (bootstrapping) {
    return <p className="auth-loading">Comprobando sesión…</p>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (!hasActiveTenant) {
    return <Navigate to="/seleccionar-gimnasio" replace />;
  }
  return <Outlet />;
}

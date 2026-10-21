import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  GymApiError,
  getCsrfToken,
  setCsrfToken,
  setGymCsrfRecoveryHandler,
  setGymSessionExpiredHandler,
} from "../../api/gymHttpClient.js";
import {
  fetchGymMemberships,
  fetchGymSession,
  gymLogin,
  gymLogout,
  selectGymTenant,
} from "../../api/gymAuthApi.js";
import { createOperationalRequestGuard } from "../operationalRequestGuard.js";

const GymAuthContext = createContext(null);

export function GymAuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [memberships, setMemberships] = useState([]);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [operationalGeneration, setOperationalGeneration] = useState(0);
  const refreshInFlightRef = useRef(null);
  const operationalGuardRef = useRef(null);
  if (!operationalGuardRef.current) {
    operationalGuardRef.current = createOperationalRequestGuard();
  }
  const operationalGuard = operationalGuardRef.current;

  const invalidateOperationalRequests = useCallback(() => {
    operationalGuard.invalidate();
    setOperationalGeneration(operationalGuard.getGeneration());
  }, [operationalGuard]);

  const clearOperationalState = useCallback(() => {
    setMemberships([]);
    invalidateOperationalRequests();
  }, [invalidateOperationalRequests]);

  const handleSessionExpired = useCallback(() => {
    setSession(null);
    setMemberships([]);
    setCsrfToken(null);
    invalidateOperationalRequests();
  }, [invalidateOperationalRequests]);

  const applySession = useCallback((body) => {
    setSession(body);
    setError(null);
  }, []);

  const refreshSession = useCallback(async () => {
    if (refreshInFlightRef.current) {
      return refreshInFlightRef.current;
    }
    const run = (async () => {
      try {
        const body = await fetchGymSession();
        applySession(body);
        return body;
      } catch (err) {
        if (err instanceof GymApiError && err.status === 401) {
          handleSessionExpired();
          return null;
        }
        throw err;
      } finally {
        if (refreshInFlightRef.current === run) {
          refreshInFlightRef.current = null;
        }
      }
    })();
    refreshInFlightRef.current = run;
    return run;
  }, [applySession, handleSessionExpired]);

  useEffect(() => {
    setGymSessionExpiredHandler(handleSessionExpired);
    setGymCsrfRecoveryHandler(async () => {
      await refreshSession();
    });
    return () => {
      setGymSessionExpiredHandler(null);
      setGymCsrfRecoveryHandler(null);
    };
  }, [handleSessionExpired, refreshSession]);

  const loadMemberships = useCallback(async () => {
    const rows = await fetchGymMemberships();
    setMemberships(rows);
    return rows;
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await refreshSession();
      } catch {
        if (!cancelled) {
          setError("No se pudo recuperar la sesión.");
        }
      } finally {
        if (!cancelled) {
          setBootstrapping(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshSession]);

  const login = useCallback(
    async ({ email, password }) => {
      setBusy(true);
      setError(null);
      try {
        await gymLogin({ email, password });
        const body = await refreshSession();
        if (body) {
          await loadMemberships();
        }
        return body;
      } catch (err) {
        const message =
          err instanceof GymApiError ? err.message : "No se pudo iniciar sesión.";
        setError(message);
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [loadMemberships, refreshSession],
  );

  const logout = useCallback(async () => {
    setBusy(true);
    setError(null);
    invalidateOperationalRequests();
    try {
      const attemptLogout = async () => gymLogout();
      try {
        await attemptLogout();
      } catch (err) {
        const needsCsrfRefresh =
          err instanceof GymApiError &&
          (err.status === 403 || !getCsrfToken());
        if (needsCsrfRefresh) {
          await refreshSession();
          await attemptLogout();
        } else {
          throw err;
        }
      }
      handleSessionExpired();
    } catch (err) {
      const message =
        err instanceof GymApiError
          ? err.message
          : "No se pudo cerrar sesión en el servidor.";
      setError(message);
      throw err;
    } finally {
      setBusy(false);
    }
  }, [handleSessionExpired, invalidateOperationalRequests, refreshSession]);

  const chooseTenant = useCallback(
    async (tenantId) => {
      setBusy(true);
      setError(null);
      invalidateOperationalRequests();
      try {
        await selectGymTenant(tenantId);
        const body = await refreshSession();
        invalidateOperationalRequests();
        return body;
      } catch (err) {
        const message =
          err instanceof GymApiError ? err.message : "No se pudo seleccionar el gimnasio.";
        setError(message);
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [invalidateOperationalRequests, refreshSession],
  );

  const beginOperationalRequest = useCallback(() => {
    const generation = operationalGuard.getGeneration();
    return { generation, signal: operationalGuard.getSignal() };
  }, [operationalGuard]);

  const isOperationalResponseStale = useCallback(
    (requestGeneration) => operationalGuard.isStale(requestGeneration),
    [operationalGuard],
  );

  const value = useMemo(
    () => ({
      session,
      memberships,
      bootstrapping,
      busy,
      error,
      setError,
      operationalGeneration,
      isAuthenticated: Boolean(session?.user_id),
      hasActiveTenant: Boolean(session?.active_tenant_id),
      login,
      logout,
      refreshSession,
      loadMemberships,
      chooseTenant,
      clearOperationalState,
      beginOperationalRequest,
      isOperationalResponseStale,
      invalidateOperationalRequests,
    }),
    [
      session,
      memberships,
      bootstrapping,
      busy,
      error,
      operationalGeneration,
      login,
      logout,
      refreshSession,
      loadMemberships,
      chooseTenant,
      clearOperationalState,
      beginOperationalRequest,
      isOperationalResponseStale,
      invalidateOperationalRequests,
    ],
  );

  return <GymAuthContext.Provider value={value}>{children}</GymAuthContext.Provider>;
}

export function useGymAuth() {
  const ctx = useContext(GymAuthContext);
  if (!ctx) {
    throw new Error("useGymAuth debe usarse dentro de GymAuthProvider.");
  }
  return ctx;
}

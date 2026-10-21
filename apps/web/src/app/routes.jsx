import { createBrowserRouter, Navigate } from "react-router-dom";
import { PublicOnlyRoute, RequireActiveTenant, RequireGymAuth } from "./AuthGate.jsx";
import GymAuthLayout from "./GymAuthLayout.jsx";
import OperationalAppLayout from "./OperationalAppLayout.jsx";
import { ROUTE_PATHS } from "./routePaths.js";
import AppShell from "./AppShell.jsx";
import AttendancePage from "../pages/AttendancePage.jsx";
import BranchesPage from "../pages/BranchesPage.jsx";
import DashboardPage from "../pages/DashboardPage.jsx";
import LandingPage from "../pages/LandingPage.jsx";
import LoginPage from "../pages/LoginPage.jsx";
import MembersPage from "../pages/MembersPage.jsx";
import MembershipsPage from "../pages/MembershipsPage.jsx";
import NotFoundPage from "../pages/NotFoundPage.jsx";
import SettingsPage from "../pages/SettingsPage.jsx";
import TenantSelectPage from "../pages/TenantSelectPage.jsx";

export const router = createBrowserRouter([
  {
    path: ROUTE_PATHS.landing,
    element: <LandingPage />,
  },
  {
    element: <GymAuthLayout />,
    children: [
      {
        path: ROUTE_PATHS.login,
        element: <PublicOnlyRoute />,
        children: [{ index: true, element: <LoginPage /> }],
      },
      {
        element: <RequireGymAuth />,
        children: [
          {
            path: ROUTE_PATHS.tenantSelect,
            element: <TenantSelectPage />,
          },
          {
            element: <RequireActiveTenant />,
            children: [
              {
                element: <OperationalAppLayout />,
                children: [
                  {
                    element: <AppShell />,
                    children: [
                      { path: "socios", element: <MembersPage /> },
                      { path: "membresias", element: <MembershipsPage /> },
                      { path: "asistencias", element: <AttendancePage /> },
                      { path: "sucursales", element: <BranchesPage /> },
                      { path: "configuracion", element: <SettingsPage /> },
                      { path: "dashboard", element: <DashboardPage /> },
                      { path: "*", element: <NotFoundPage /> },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to={ROUTE_PATHS.landing} replace /> },
]);

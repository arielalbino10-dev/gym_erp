import { createBrowserRouter } from "react-router-dom";
import AppShell from "./AppShell.jsx";
import AttendancePage from "../pages/AttendancePage.jsx";
import BranchesPage from "../pages/BranchesPage.jsx";
import DashboardPage from "../pages/DashboardPage.jsx";
import MembersPage from "../pages/MembersPage.jsx";
import MembershipsPage from "../pages/MembershipsPage.jsx";
import NotFoundPage from "../pages/NotFoundPage.jsx";
import SettingsPage from "../pages/SettingsPage.jsx";

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "socios", element: <MembersPage /> },
      { path: "membresias", element: <MembershipsPage /> },
      { path: "asistencias", element: <AttendancePage /> },
      { path: "sucursales", element: <BranchesPage /> },
      { path: "configuracion", element: <SettingsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

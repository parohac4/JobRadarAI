import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import JobDetailPage from "./pages/JobDetailPage";
import JobsPage from "./pages/JobsPage";
import LoginPage from "./pages/LoginPage";
import SettingsPage from "./pages/SettingsPage";
import { getToken } from "./api";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const hasSession = getToken() || sessionStorage.getItem("jobradar_session") === "1";
  if (!hasSession) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<JobsPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobDetailPage />} />
        <Route path="sources" element={<Navigate to="/settings" replace />} />
        <Route path="applications" element={<Navigate to="/" replace />} />
        <Route path="profile" element={<Navigate to="/settings" replace />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

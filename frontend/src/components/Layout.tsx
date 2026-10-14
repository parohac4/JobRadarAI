import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { apiClient, setToken } from "../api";

export default function Layout() {
  const [demoMode, setDemoMode] = useState(false);

  useEffect(() => {
    apiClient.get<{ demo_mode: boolean }>("/system/health").then((h) => setDemoMode(h.demo_mode));
  }, []);

  const toggleTheme = () => {
    const root = document.documentElement;
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("jobradar_theme", next);
  };

  useEffect(() => {
    const saved = localStorage.getItem("jobradar_theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  }, []);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">JobRadar AI</div>
        {demoMode && <span className="muted">Demo režim</span>}
        <nav className="nav">
          <NavLink to="/" end>Přehled</NavLink>
          <NavLink to="/jobs">Nabídky</NavLink>
          <NavLink to="/applications">Žádosti</NavLink>
          <NavLink to="/profile">Profil</NavLink>
          <NavLink to="/settings">Nastavení</NavLink>
        </nav>
        <div className="row">
          <button type="button" className="btn secondary" onClick={toggleTheme}>Světlý / tmavý</button>
          <button
            type="button"
            className="btn secondary"
            onClick={() => {
              setToken(null);
              window.location.href = "/login";
            }}
          >
            Odhlásit
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

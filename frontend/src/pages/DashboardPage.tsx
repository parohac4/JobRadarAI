import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../api";
import type { DashboardStats, JobListing } from "../types";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [jobs, setJobs] = useState<JobListing[]>([]);

  useEffect(() => {
    apiClient.get<DashboardStats>("/dashboard/stats").then(setStats);
    apiClient.get<JobListing[]>("/jobs?limit=5").then(setJobs);
  }, []);

  const recommended = jobs
    .filter((j) => (j.latest_score ?? 0) >= 60)
    .sort((a, b) => (b.latest_score ?? 0) - (a.latest_score ?? 0));

  return (
    <div className="grid">
      <h1>Přehled</h1>
      <div className="grid stats">
        <div className="card"><div className="muted">Nabídky</div><div className="stat-value">{stats?.total_jobs ?? "–"}</div></div>
        <div className="card"><div className="muted">Otevřené</div><div className="stat-value">{stats?.open_jobs ?? "–"}</div></div>
        <div className="card"><div className="muted">Aktivní žádosti</div><div className="stat-value">{stats?.applications_active ?? "–"}</div></div>
        <div className="card"><div className="muted">Průměrné skóre</div><div className="stat-value">{stats?.avg_score?.toFixed(0) ?? "–"}</div></div>
      </div>
      <section className="card">
        <h2>Doporučené pozice</h2>
        {recommended.length === 0 && <p className="muted">Zatím bez hodnocení – otevřete nabídku a spusťte AI analýzu.</p>}
        <table>
          <thead>
            <tr><th>Pozice</th><th>Firma</th><th>Skóre</th></tr>
          </thead>
          <tbody>
            {recommended.map((j) => (
              <tr key={j.id}>
                <td><Link to={`/jobs/${j.id}`}>{j.title}</Link></td>
                <td>{j.company}</td>
                <td><span className="score-pill">{j.latest_score}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

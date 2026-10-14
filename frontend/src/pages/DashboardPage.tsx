import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient, errorText } from "../api";
import type { DashboardStats, JobListing } from "../types";

const RECOMMENDED_MIN_SCORE = 60;

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recommended, setRecommended] = useState<JobListing[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiClient.get<DashboardStats>("/dashboard/stats").then(setStats),
      apiClient
        .get<JobListing[]>(`/jobs?sort=score&min_score=${RECOMMENDED_MIN_SCORE}&limit=5`)
        .then(setRecommended),
    ]).catch((err) => setError(errorText(err)));
  }, []);

  return (
    <div className="grid">
      <h1>Přehled</h1>
      {error && <p className="error">{error}</p>}
      <div className="grid stats">
        <div className="card"><div className="muted">Nabídky</div><div className="stat-value">{stats?.total_jobs ?? "–"}</div></div>
        <div className="card"><div className="muted">Otevřené</div><div className="stat-value">{stats?.open_jobs ?? "–"}</div></div>
        <div className="card"><div className="muted">Aktivní žádosti</div><div className="stat-value">{stats?.applications_active ?? "–"}</div></div>
        <div className="card"><div className="muted">Průměrné skóre</div><div className="stat-value">{stats?.avg_score?.toFixed(0) ?? "–"}</div></div>
      </div>
      <section className="card">
        <h2>Doporučené pozice</h2>
        {recommended.length === 0 ? (
          <p className="muted">
            Zatím žádná nabídka se skóre {RECOMMENDED_MIN_SCORE}+ – otevřete nabídku a spusťte AI hodnocení.
          </p>
        ) : (
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
        )}
      </section>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient, errorText } from "../api";
import { APPLICATION_STATUS_LABELS, type Application } from "../types";

export default function ApplicationsPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [error, setError] = useState("");

  const reload = () =>
    apiClient
      .get<Application[]>("/applications")
      .then(setApps)
      .catch((err) => setError(errorText(err)));
  useEffect(() => {
    reload();
  }, []);

  async function changeStatus(app: Application, status: string) {
    setError("");
    try {
      await apiClient.patch(`/applications/${app.id}/status`, { status, note: "" });
      await reload();
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <div className="grid">
      <h1>Evidence výběrových řízení</h1>
      {error && <p className="error" role="alert">{error}</p>}
      <section className="card">
        <table>
          <thead>
            <tr><th>Pozice</th><th>Stav</th><th>Aktualizace</th><th>Akce</th></tr>
          </thead>
          <tbody>
            {apps.map((a) => (
              <tr key={a.id}>
                <td>
                  <Link to={`/jobs/${a.job_listing_id}`}>{a.job_title}</Link>
                  <div className="muted">{a.company}</div>
                </td>
                <td>{APPLICATION_STATUS_LABELS[a.status] || a.status}</td>
                <td>{new Date(a.updated_at).toLocaleString("cs-CZ")}</td>
                <td>
                  <select
                    aria-label="Stav žádosti"
                    value={a.status}
                    onChange={(e) => changeStatus(a, e.target.value)}
                  >
                    {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {apps.length === 0 && <p className="muted">Zatím žádné žádosti – vytvořte je z detailu nabídky.</p>}
      </section>
    </div>
  );
}

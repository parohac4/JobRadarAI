import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../api";
import { APPLICATION_STATUS_LABELS, type Application } from "../types";

export default function ApplicationsPage() {
  const [apps, setApps] = useState<Application[]>([]);

  const reload = () => apiClient.get<Application[]>("/applications").then(setApps);
  useEffect(() => {
    reload();
  }, []);

  async function changeStatus(app: Application, status: string) {
    await apiClient.patch(`/applications/${app.id}/status`, { status, note: "" });
    await reload();
  }

  return (
    <div className="grid">
      <h1>Evidence výběrových řízení</h1>
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

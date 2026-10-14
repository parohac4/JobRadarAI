import { useEffect, useState } from "react";
import { apiClient, errorText } from "../api";

type Health = { status: string; demo_mode: boolean };
type SyncRun = { id: number; source: string; status: string; message: string; started_at: string };
type AuditEvent = { id: number; action: string; entity_type: string; entity_id: string; payload: Record<string, unknown>; created_at: string };

const ACTION_LABELS: Record<string, string> = {
  "auth.login": "Přihlášení",
  "auth.login_failed": "Neúspěšné přihlášení",
  "job.create": "Nabídka přidána",
  "job.import_url": "Import z URL",
  "job.import_email": "Import z e-mailu",
  "job.evaluate": "AI hodnocení",
  "job.generate_response": "Návrh reakce",
  "application.create": "Žádost založena",
  "application.status": "Změna stavu žádosti",
  "application.note": "Poznámka k žádosti",
  "profile.update": "Úprava profilu",
};

export default function SettingsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [syncRuns, setSyncRuns] = useState<SyncRun[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    apiClient.get<Health>("/system/health").then(setHealth).catch(() => setHealth({ status: "nedostupné", demo_mode: false }));
    apiClient.get<SyncRun[]>("/system/sync-runs").then(setSyncRuns).catch(() => setSyncRuns([]));
    apiClient.get<AuditEvent[]>("/system/audit").then(setAudit).catch((err) => setError(errorText(err)));
  }, []);

  async function resetDemo() {
    setMsg("");
    setError("");
    try {
      const res = await apiClient.post<{ ok: boolean; jobs_created?: number }>("/system/demo/reset");
      setMsg(`Demo data obnovena (${res.jobs_created ?? 0} nabídek).`);
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <div className="grid">
      <h1>Nastavení a provoz</h1>
      <section className="card grid">
        <h2>Stav systému</h2>
        <p>API: {health?.status ?? "…"} · Demo režim: {health?.demo_mode ? "ano" : "ne"}</p>
        <p className="muted">
          AI poskytovatel, e-mail IMAP a zdroje RSS se konfigurují v souboru <code>.env</code> na serveru
          (viz dokumentace). Bez API klíče běží heuristické (mock) hodnocení.
        </p>
        {health?.demo_mode && (
          <button className="btn secondary" type="button" onClick={resetDemo}>Obnovit demo data</button>
        )}
        {msg && <p className="muted" role="status">{msg}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </section>
      <section className="card">
        <h2>Poslední aktivity (audit log)</h2>
        {audit.length === 0 ? (
          <p className="muted">Zatím bez záznamů.</p>
        ) : (
          <table>
            <thead><tr><th>Čas</th><th>Událost</th><th>Objekt</th></tr></thead>
            <tbody>
              {audit.map((a) => (
                <tr key={a.id}>
                  <td>{new Date(a.created_at).toLocaleString("cs-CZ")}</td>
                  <td>{ACTION_LABELS[a.action] || a.action}</td>
                  <td>{a.entity_type ? `${a.entity_type} #${a.entity_id}` : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section className="card">
        <h2>Automatické synchronizace</h2>
        {syncRuns.length === 0 ? (
          <p className="muted">Zatím bez záznamů – plánovaný worker (RSS / IMAP) přibude v etapě 3. Importy se nyní spouštějí ručně.</p>
        ) : (
          <table>
            <thead><tr><th>Zdroj</th><th>Stav</th><th>Zpráva</th><th>Čas</th></tr></thead>
            <tbody>
              {syncRuns.map((r) => (
                <tr key={r.id}>
                  <td>{r.source}</td>
                  <td>{r.status}</td>
                  <td>{r.message}</td>
                  <td>{new Date(r.started_at).toLocaleString("cs-CZ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

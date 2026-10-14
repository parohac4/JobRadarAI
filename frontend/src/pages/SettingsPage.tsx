import { useEffect, useState } from "react";
import { apiClient } from "../api";

type Health = { status: string; demo_mode: boolean };
type SyncRun = { id: number; source: string; status: string; message: string; started_at: string };

export default function SettingsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [syncRuns, setSyncRuns] = useState<SyncRun[]>([]);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    apiClient.get<Health>("/system/health").then(setHealth);
    apiClient.get<SyncRun[]>("/system/sync-runs").then(setSyncRuns).catch(() => setSyncRuns([]));
  }, []);

  async function resetDemo() {
    const res = await apiClient.post<{ ok: boolean; message?: string; jobs_created?: number }>("/system/demo/reset");
    setMsg(res.ok ? `Demo data obnovena (${res.jobs_created} nabídek).` : res.message || "Nepodařilo se");
  }

  return (
    <div className="grid">
      <h1>Nastavení a provoz</h1>
      <section className="card grid">
        <h2>Stav systému</h2>
        <p>API: {health?.status ?? "…"} · Demo režim: {health?.demo_mode ? "ano" : "ne"}</p>
        <p className="muted">
          AI poskytovatel, e-mail IMAP a zdroje RSS se konfigurují v souboru <code>.env</code> na serveru
          (viz dokumentace). Bez API klíče běží mock hodnocení.
        </p>
        {health?.demo_mode && (
          <button className="btn secondary" type="button" onClick={resetDemo}>Obnovit demo data</button>
        )}
        {msg && <p className="muted">{msg}</p>}
      </section>
      <section className="card">
        <h2>Poslední synchronizace / importy</h2>
        {syncRuns.length === 0 ? (
          <p className="muted">Zatím bez záznamů – plánovaný worker přibude v etapě 3.</p>
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

import { FormEvent, useEffect, useState } from "react";
import { apiClient, errorText } from "../api";

type Health = { status: string; demo_mode: boolean };
type SyncRun = { id: number; source: string; status: string; message: string; started_at: string };
type AuditEvent = { id: number; action: string; entity_type: string; entity_id: string; payload: Record<string, unknown>; created_at: string };
type Integrations = {
  imap_configured: boolean;
  imap_folder: string;
  notify_enabled: boolean;
  notify_min_score: number;
  auto_evaluate_on_import: boolean;
  ai_provider: string;
  worker_enabled: boolean;
  sync_interval_seconds: number;
};
type Feed = { id: number; title: string; url: string; enabled: boolean; last_error: string };

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
  "profile.cv_import": "Import CV",
  "feed.create": "RSS zdroj",
};

export default function SettingsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [integrations, setIntegrations] = useState<Integrations | null>(null);
  const [syncRuns, setSyncRuns] = useState<SyncRun[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [feedUrl, setFeedUrl] = useState("");
  const [feedTitle, setFeedTitle] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const reloadSync = () => apiClient.get<SyncRun[]>("/system/sync-runs").then(setSyncRuns).catch(() => setSyncRuns([]));

  useEffect(() => {
    apiClient.get<Health>("/system/health").then(setHealth).catch(() => setHealth({ status: "nedostupné", demo_mode: false }));
    apiClient.get<Integrations>("/system/integrations").then(setIntegrations).catch(() => setIntegrations(null));
    reloadSync();
    apiClient.get<AuditEvent[]>("/system/audit").then(setAudit).catch((err) => setError(errorText(err)));
    apiClient.get<Feed[]>("/feeds").then(setFeeds).catch(() => setFeeds([]));
  }, []);

  async function runSync(kind: "imap" | "rss") {
    setBusy(true);
    setMsg("");
    setError("");
    try {
      const res = await apiClient.post<Record<string, unknown>>(`/system/sync/${kind}`);
      setMsg(`${kind.toUpperCase()} sync: ${JSON.stringify(res)}`);
      await reloadSync();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function addFeed(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await apiClient.post("/feeds", { title: feedTitle, url: feedUrl, enabled: true });
      setFeedTitle("");
      setFeedUrl("");
      setFeeds(await apiClient.get<Feed[]>("/feeds"));
      setMsg("RSS zdroj přidán.");
    } catch (err) {
      setError(errorText(err));
    }
  }

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
        {integrations && (
          <ul className="muted">
            <li>IMAP: {integrations.imap_configured ? `aktivní (složka ${integrations.imap_folder})` : "nekonfigurováno v .env"}</li>
            <li>Worker: {integrations.worker_enabled ? `ano, každých ${integrations.sync_interval_seconds} s` : "vypnutý"}</li>
            <li>AI: {integrations.ai_provider} · auto-hodnocení po importu: {integrations.auto_evaluate_on_import ? "ano" : "ne"}</li>
            <li>Notifikace: {integrations.notify_enabled ? `ano, od skóre ${integrations.notify_min_score}` : "ne"}</li>
          </ul>
        )}
        <p className="muted">
          Gmail IMAP, SMTP, Telegram a OpenAI nastavíte v <code>.env</code> – návod{" "}
          <a href="https://github.com/parohac4/JobRadarAI/blob/main/docs/07-ETAPA2-PLAN.md" target="_blank" rel="noreferrer">
            docs/07-ETAPA2-PLAN.md
          </a>
          .
        </p>
        <div className="row">
          <button className="btn secondary" type="button" disabled={busy || !integrations?.imap_configured} onClick={() => runSync("imap")}>
            Sync IMAP teď
          </button>
          <button className="btn secondary" type="button" disabled={busy} onClick={() => runSync("rss")}>
            Sync RSS teď
          </button>
        </div>
        {health?.demo_mode && (
          <button className="btn secondary" type="button" onClick={resetDemo}>Obnovit demo data</button>
        )}
        {msg && <p className="muted" role="status">{msg}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      <section className="card grid">
        <h2>RSS zdroje</h2>
        <form className="grid" onSubmit={addFeed}>
          <input placeholder="Název (volitelné)" value={feedTitle} onChange={(e) => setFeedTitle(e.target.value)} />
          <input placeholder="https://…/feed.xml" value={feedUrl} onChange={(e) => setFeedUrl(e.target.value)} required type="url" />
          <button className="btn" type="submit">Přidat feed</button>
        </form>
        {feeds.length === 0 ? (
          <p className="muted">Zatím žádné RSS – přidejte veřejný feed (Jobs.cz / firemní kariérní stránky s RSS).</p>
        ) : (
          <ul>
            {feeds.map((f) => (
              <li key={f.id}>
                <strong>{f.title || f.url}</strong>
                {f.last_error && <span className="error"> – {f.last_error}</span>}
              </li>
            ))}
          </ul>
        )}
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
        <h2>Historie synchronizací</h2>
        {syncRuns.length === 0 ? (
          <p className="muted">Zatím bez záznamů – spusťte sync nebo počkejte na worker.</p>
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

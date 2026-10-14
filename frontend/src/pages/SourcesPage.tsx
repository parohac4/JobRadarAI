import { useState } from "react";
import { apiClient, errorText } from "../api";
import FeedSourcesPanel from "../components/FeedSourcesPanel";

export default function SourcesPage() {
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [syncBusy, setSyncBusy] = useState(false);

  async function runSyncRss() {
    setSyncBusy(true);
    setMsg("");
    setError("");
    try {
      const res = await apiClient.post<Record<string, unknown>>("/system/sync/rss");
      setMsg(`RSS sync dokončen: ${JSON.stringify(res)}`);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSyncBusy(false);
    }
  }

  return (
    <div className="grid">
      <h1>Zdroje nabídek (RSS / API)</h1>
      <p className="muted">
        Tady spravujete kanály, ze kterých JobRadar stahuje inzeráty. Výchozí zdroje (Kariera.cz, Síť práce, …)
        se doplní automaticky při otevření stránky nebo po restartu backendu.
      </p>
      {msg && <p className="muted" role="status">{msg}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <section className="card">
        <FeedSourcesPanel onSyncRss={runSyncRss} syncBusy={syncBusy} />
      </section>
    </div>
  );
}

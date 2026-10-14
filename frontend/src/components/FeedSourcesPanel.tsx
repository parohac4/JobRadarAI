import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiClient, errorText } from "../api";

export type Feed = {
  id: number;
  title: string;
  url: string;
  enabled: boolean;
  last_error: string;
};

type Props = {
  onSyncRss?: () => void;
  syncBusy?: boolean;
};

export default function FeedSourcesPanel({ onSyncRss, syncBusy }: Props) {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedUrl, setFeedUrl] = useState("");
  const [feedTitle, setFeedTitle] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const list = await apiClient.get<Feed[]>("/feeds");
      setFeeds(list);
    } catch (err) {
      setFeeds([]);
      setError(
        `${errorText(err)} – pokud vidíte 404, nasaďte nový backend (endpoint /feeds).`,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function ensureDefaults() {
    setBusy(true);
    setError("");
    try {
      const res = await apiClient.post<{ added: number }>("/feeds/ensure-defaults");
      setMsg(res.added > 0 ? `Doplněno ${res.added} výchozích zdrojů.` : "Všechny výchozí zdroje už máte.");
      await reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function setFeedEnabled(feed: Feed, enabled: boolean) {
    setBusy(true);
    setError("");
    try {
      const updated = await apiClient.patch<Feed>(`/feeds/${feed.id}`, { enabled });
      setFeeds((list) => list.map((f) => (f.id === feed.id ? updated : f)));
      setMsg(enabled ? "Zdroj zapnut." : "Zdroj vypnut – sync ho přeskočí.");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function addFeed(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiClient.post("/feeds", { title: feedTitle, url: feedUrl, enabled: true });
      setFeedTitle("");
      setFeedUrl("");
      setMsg("Zdroj přidán.");
      await reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const enabledCount = feeds.filter((f) => f.enabled).length;

  return (
    <div className="grid">
      <p className="muted">
        Zaškrtnutím <strong>Zap.</strong> zapnete nebo vypnete synchronizaci daného kanálu (RSS, JSON API).
        Vypnuté zdroje worker i tlačítko „Sync RSS“ přeskočí.
      </p>
      <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
        {onSyncRss && (
          <button className="btn" type="button" disabled={syncBusy || busy} onClick={onSyncRss}>
            Sync RSS teď
          </button>
        )}
        <button className="btn secondary" type="button" disabled={busy} onClick={() => reload()}>
          Obnovit seznam
        </button>
        <button className="btn secondary" type="button" disabled={busy} onClick={ensureDefaults}>
          Doplnit výchozí zdroje
        </button>
      </div>
      {msg && <p className="muted" role="status">{msg}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      <form className="grid" onSubmit={addFeed}>
        <h3>Přidat vlastní zdroj</h3>
        <input placeholder="Název (volitelné)" value={feedTitle} onChange={(e) => setFeedTitle(e.target.value)} />
        <input
          placeholder="https://…/feed.xml"
          value={feedUrl}
          onChange={(e) => setFeedUrl(e.target.value)}
          required
          type="url"
        />
        <button className="btn secondary" type="submit" disabled={busy}>Přidat</button>
      </form>

      {loading ? (
        <p>Načítání zdrojů…</p>
      ) : feeds.length === 0 ? (
        <p className="error">
          Seznam je prázdný. Klikněte na „Doplnit výchozí zdroje“ (Kariera.cz, Síť práce, …) nebo přidejte URL ručně.
        </p>
      ) : (
        <>
          <p className="muted">Celkem {feeds.length} zdrojů, zapnuto {enabledCount}.</p>
          <table>
            <thead>
              <tr>
                <th>Zap.</th>
                <th>Název</th>
                <th>URL</th>
                <th>Poslední chyba</th>
              </tr>
            </thead>
            <tbody>
              {feeds.map((f) => (
                <tr key={f.id} className={f.enabled ? undefined : "muted"}>
                  <td>
                    <input
                      type="checkbox"
                      checked={f.enabled}
                      disabled={busy}
                      aria-label={`Zapnout zdroj ${f.title || f.url}`}
                      onChange={(e) => setFeedEnabled(f, e.target.checked)}
                    />
                  </td>
                  <td>{f.title || "—"}</td>
                  <td style={{ maxWidth: "360px", wordBreak: "break-all" }}>{f.url}</td>
                  <td className="error">{f.last_error || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

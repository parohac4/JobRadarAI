import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient, errorText } from "../api";
import type { JobListing, Profile } from "../types";
import { safeHref } from "../utils/safeUrl";

type JobSort = "imported" | "score" | "distance";
type InboxFilter = "active" | "snoozed" | "dismissed";

const INBOX_LABELS: Record<InboxFilter, string> = {
  active: "Aktivní",
  snoozed: "Odložené",
  dismissed: "Zamítnuté",
};

function formatDistance(j: JobListing): string {
  if (j.location_remote) return "remote";
  if (j.distance_km != null) return `${j.distance_km} km`;
  if (j.location_unknown) return "?";
  return "–";
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [hasHome, setHasHome] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [url, setUrl] = useState("");
  const [rawText, setRawText] = useState("");
  const [importUrl, setImportUrl] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [maxKm, setMaxKm] = useState("");
  const [sort, setSort] = useState<JobSort>("imported");
  const [includeRemote, setIncludeRemote] = useState(true);
  const [includeUnknown, setIncludeUnknown] = useState(true);
  const [inbox, setInbox] = useState<InboxFilter>("active");

  const reload = useCallback(() => {
    const params = new URLSearchParams();
    if (inbox !== "active") params.set("inbox", inbox);
    if (maxKm.trim()) params.set("max_km", maxKm.trim());
    if (sort !== "imported") params.set("sort", sort);
    if (!includeRemote) params.set("include_remote", "false");
    if (!includeUnknown) params.set("include_unknown", "false");
    const qs = params.toString();
    return apiClient
      .get<JobListing[]>(`/jobs${qs ? `?${qs}` : ""}`)
      .then(setJobs)
      .catch((err) => setError(errorText(err)));
  }, [inbox, maxKm, sort, includeRemote, includeUnknown]);

  useEffect(() => {
    apiClient
      .get<Profile>("/profile")
      .then((p) => {
        const prefs = p.preferences || {};
        const home = prefs.home as { city?: string } | undefined;
        setHasHome(Boolean(home?.city || prefs.home_city));
        if (prefs.max_distance_km != null && prefs.max_distance_km !== "" && !maxKm) {
          setMaxKm(String(prefs.max_distance_km));
        }
      })
      .catch(() => setHasHome(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function run(action: () => Promise<unknown>, reset: () => void) {
    setError("");
    setBusy(true);
    try {
      await action();
      reset();
      await reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  function addManual(e: FormEvent) {
    e.preventDefault();
    run(
      () => apiClient.post("/jobs", { title, company, location, url, raw_text: rawText, source: "manual" }),
      () => {
        setTitle("");
        setCompany("");
        setLocation("");
        setUrl("");
        setRawText("");
      },
    );
  }

  function doImportUrl(e: FormEvent) {
    e.preventDefault();
    run(() => apiClient.post("/jobs/import/url", { url: importUrl }), () => setImportUrl(""));
  }

  function doImportEmail(e: FormEvent) {
    e.preventDefault();
    run(
      () => apiClient.post("/jobs/import/email", { email_body: emailBody, subject: emailSubject }),
      () => {
        setEmailSubject("");
        setEmailBody("");
      },
    );
  }

  return (
    <div className="grid">
      <h1>Pracovní nabídky</h1>
      <p className="muted">
        Import ze RSS/API:{" "}
        <Link to="/sources"><strong>Zdroje RSS</strong></Link> – zapínání kanálů (Kariera.cz, Síť práce, …).
      </p>
      {error && <p className="error" role="alert">{error}</p>}

      <section className="card grid">
        <h2>Seznam nabídek</h2>
        <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
          {(Object.keys(INBOX_LABELS) as InboxFilter[]).map((key) => (
            <button
              key={key}
              type="button"
              className={inbox === key ? "btn" : "btn secondary"}
              onClick={() => setInbox(key)}
            >
              {INBOX_LABELS[key]}
            </button>
          ))}
        </div>
      </section>

      <section className="card grid">
        <h2>Filtr podle vzdálenosti</h2>
        {!hasHome && (
          <p className="muted">
            Nastavte <Link to="/profile">domovské město v profilu</Link> (např. Strakonice), pak uvidíte vzdálenost a filtr.
          </p>
        )}
        <div className="row" style={{ flexWrap: "wrap", gap: "0.75rem", alignItems: "flex-end" }}>
          <label>
            Max. vzdálenost (km)
            <input
              type="number"
              min={1}
              max={500}
              value={maxKm}
              onChange={(e) => setMaxKm(e.target.value)}
              placeholder="bez limitu"
              disabled={!hasHome}
            />
          </label>
          <label>
            Řazení
            <select value={sort} onChange={(e) => setSort(e.target.value as JobSort)} disabled={!hasHome && sort === "distance"}>
              <option value="imported">Nejnovější</option>
              <option value="score">Podle skóre</option>
              <option value="distance" disabled={!hasHome}>Nejbližší</option>
            </select>
          </label>
          <label className="row">
            <input
              type="checkbox"
              checked={includeRemote}
              onChange={(e) => setIncludeRemote(e.target.checked)}
              disabled={!hasHome}
            />
            Zahrnout remote / hybrid
          </label>
          <label className="row">
            <input
              type="checkbox"
              checked={includeUnknown}
              onChange={(e) => setIncludeUnknown(e.target.checked)}
              disabled={!hasHome}
            />
            Neznámá lokalita
          </label>
        </div>
        <p className="muted">
          Vzdálenost se počítá z textu lokality inzerátu (okresní města v ČR). Remote nabídky nemají km.
        </p>
      </section>

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
        <form className="card grid" onSubmit={addManual}>
          <h3>Ruční přidání</h3>
          <input aria-label="Název pozice" placeholder="Název pozice" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <input aria-label="Zaměstnavatel" placeholder="Zaměstnavatel" value={company} onChange={(e) => setCompany(e.target.value)} />
          <input aria-label="Lokalita" placeholder="Lokalita" value={location} onChange={(e) => setLocation(e.target.value)} />
          <input aria-label="URL" placeholder="URL" type="url" value={url} onChange={(e) => setUrl(e.target.value)} />
          <textarea aria-label="Text inzerátu" placeholder="Text inzerátu" rows={5} value={rawText} onChange={(e) => setRawText(e.target.value)} />
          <button className="btn" type="submit" disabled={busy}>Uložit</button>
        </form>
        <form className="card grid" onSubmit={doImportUrl}>
          <h3>Import z URL</h3>
          <input aria-label="URL inzerátu" placeholder="https://..." type="url" value={importUrl} onChange={(e) => setImportUrl(e.target.value)} required />
          <p className="muted">Načte veřejnou HTML stránku (bez obcházení ochran portálů, interní adresy jsou blokované).</p>
          <button className="btn" type="submit" disabled={busy}>Importovat</button>
        </form>
        <form className="card grid" onSubmit={doImportEmail}>
          <h3>Import z e-mailu</h3>
          <input aria-label="Předmět e-mailu" placeholder="Předmět e-mailu (volitelné)" value={emailSubject} onChange={(e) => setEmailSubject(e.target.value)} />
          <textarea aria-label="Tělo e-mailu" placeholder="Vložte tělo upozornění z Jobs.cz / LinkedIn..." rows={8} value={emailBody} onChange={(e) => setEmailBody(e.target.value)} required minLength={20} />
          <button className="btn" type="submit" disabled={busy}>Parsovat e-mail</button>
        </form>
      </div>

      <section className="card">
        {jobs.length === 0 ? (
          <p className="muted">Zatím žádné nabídky – přidejte první pomocí formulářů výše.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Pozice</th>
                <th>Firma</th>
                <th>Lokalita</th>
                {hasHome && inbox === "active" && <th>Vzdálenost</th>}
                {(inbox === "snoozed" || inbox === "dismissed") && <th>Poznámka</th>}
                {inbox === "snoozed" && <th>Do kdy</th>}
                <th>Skóre</th>
                <th>Inzerát</th>
                <th>Duplicita</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => {
                const originalHref = j.url ? safeHref(j.url) : null;
                return (
                  <tr key={j.id}>
                    <td><Link to={`/jobs/${j.id}`}>{j.title}</Link></td>
                    <td>{j.company}</td>
                    <td>{j.location || "–"}</td>
                    {hasHome && inbox === "active" && <td>{formatDistance(j)}</td>}
                    {(inbox === "snoozed" || inbox === "dismissed") && (
                      <td>{inbox === "snoozed" ? j.snooze_note || "–" : j.dismissed_note || "–"}</td>
                    )}
                    {inbox === "snoozed" && (
                      <td>{j.snoozed_until ? new Date(j.snoozed_until).toLocaleDateString("cs-CZ") : "–"}</td>
                    )}
                    <td>{j.latest_score != null ? <span className="score-pill">{j.latest_score}</span> : "–"}</td>
                    <td>
                      {originalHref ? (
                        <a href={originalHref} target="_blank" rel="noopener noreferrer">Originál</a>
                      ) : (
                        "–"
                      )}
                    </td>
                    <td>{j.duplicate_of_id ? <Link to={`/jobs/${j.duplicate_of_id}`}>#{j.duplicate_of_id}</Link> : "–"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

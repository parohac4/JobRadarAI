import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient, errorText } from "../api";
import type { JobListing } from "../types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobListing[]>([]);
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

  const reload = () =>
    apiClient
      .get<JobListing[]>("/jobs")
      .then(setJobs)
      .catch((err) => setError(errorText(err)));

  useEffect(() => {
    reload();
  }, []);

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
      {error && <p className="error" role="alert">{error}</p>}

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
              <tr><th>Pozice</th><th>Firma</th><th>Lokalita</th><th>Skóre</th><th>Duplicita</th></tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td><Link to={`/jobs/${j.id}`}>{j.title}</Link></td>
                  <td>{j.company}</td>
                  <td>{j.location || "–"}</td>
                  <td>{j.latest_score != null ? <span className="score-pill">{j.latest_score}</span> : "–"}</td>
                  <td>{j.duplicate_of_id ? <Link to={`/jobs/${j.duplicate_of_id}`}>#{j.duplicate_of_id}</Link> : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

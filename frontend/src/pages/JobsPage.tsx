import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../api";
import type { JobListing } from "../types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");
  const [rawText, setRawText] = useState("");
  const [importUrl, setImportUrl] = useState("");
  const [emailBody, setEmailBody] = useState("");

  const reload = () => apiClient.get<JobListing[]>("/jobs").then(setJobs);

  useEffect(() => {
    reload();
  }, []);

  async function addManual(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await apiClient.post("/jobs", { title, company, location: "", url, raw_text: rawText, source: "manual" });
      setTitle("");
      setCompany("");
      setUrl("");
      setRawText("");
      await reload();
    } catch (err) {
      setError(String(err));
    }
  }

  async function doImportUrl(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await apiClient.post("/jobs/import/url", { url: importUrl });
      setImportUrl("");
      await reload();
    } catch (err) {
      setError(String(err));
    }
  }

  async function doImportEmail(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await apiClient.post("/jobs/import/email", { email_body: emailBody, subject: title || "Upozornění na pozici" });
      setEmailBody("");
      await reload();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="grid">
      <h1>Pracovní nabídky</h1>
      {error && <p className="error">{error}</p>}

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
        <form className="card grid" onSubmit={addManual}>
          <h3>Ruční přidání</h3>
          <input placeholder="Název pozice" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <input placeholder="Zaměstnavatel" value={company} onChange={(e) => setCompany(e.target.value)} />
          <input placeholder="URL" value={url} onChange={(e) => setUrl(e.target.value)} />
          <textarea placeholder="Text inzerátu" rows={5} value={rawText} onChange={(e) => setRawText(e.target.value)} />
          <button className="btn" type="submit">Uložit</button>
        </form>
        <form className="card grid" onSubmit={doImportUrl}>
          <h3>Import z URL</h3>
          <input placeholder="https://..." value={importUrl} onChange={(e) => setImportUrl(e.target.value)} required />
          <p className="muted">Načte veřejnou HTML stránku (bez obcházení ochran portálů).</p>
          <button className="btn" type="submit">Importovat</button>
        </form>
        <form className="card grid" onSubmit={doImportEmail}>
          <h3>Import z e-mailu</h3>
          <textarea placeholder="Vložte tělo upozornění z Jobs.cz / LinkedIn..." rows={8} value={emailBody} onChange={(e) => setEmailBody(e.target.value)} required />
          <button className="btn" type="submit">Parsovat e-mail</button>
        </form>
      </div>

      <section className="card">
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
                <td>{j.duplicate_of_id ? `#${j.duplicate_of_id}` : "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

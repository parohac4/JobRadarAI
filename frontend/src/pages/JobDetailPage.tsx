import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiClient, errorText } from "../api";
import {
  APPLICATION_STATUS_LABELS,
  type Application,
  type ApplicationHistory,
  type ApplicationNote,
  type Evaluation,
  type GeneratedResponse,
  type JobListing,
} from "../types";

function List({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <strong>{title}</strong>
      <ul>{items.map((r, i) => <li key={i}>{r}</li>)}</ul>
    </div>
  );
}

function safeHref(url: string): string | null {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.href : null;
  } catch {
    return null;
  }
}

export default function JobDetailPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const [job, setJob] = useState<JobListing | null>(null);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [drafts, setDrafts] = useState<GeneratedResponse[]>([]);
  const [responseText, setResponseText] = useState("");
  const [application, setApplication] = useState<Application | null>(null);
  const [history, setHistory] = useState<ApplicationHistory[]>([]);
  const [notes, setNotes] = useState<ApplicationNote[]>([]);
  const [noteText, setNoteText] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadApplication = useCallback(async () => {
    const app = await apiClient.get<Application | null>(`/applications/by-job/${jobId}`);
    setApplication(app);
    if (app) {
      const [h, n] = await Promise.all([
        apiClient.get<ApplicationHistory[]>(`/applications/${app.id}/history`),
        apiClient.get<ApplicationNote[]>(`/applications/${app.id}/notes`),
      ]);
      setHistory(h);
      setNotes(n);
    }
  }, [jobId]);

  const reload = useCallback(async () => {
    const [j, ev, rs] = await Promise.all([
      apiClient.get<JobListing>(`/jobs/${jobId}`),
      apiClient.get<Evaluation[]>(`/jobs/${jobId}/evaluations`),
      apiClient.get<GeneratedResponse[]>(`/jobs/${jobId}/responses`),
    ]);
    setJob(j);
    setEvaluations(ev);
    setDrafts(rs);
    setResponseText((current) => current || rs[0]?.content || "");
    await loadApplication();
  }, [jobId, loadApplication]);

  useEffect(() => {
    if (!Number.isInteger(jobId)) {
      setError("Neplatné ID nabídky");
      return;
    }
    reload().catch((err) => setError(errorText(err)));
  }, [jobId, reload]);

  async function run(action: () => Promise<void>, success: string) {
    setMessage("");
    setError("");
    setBusy(true);
    try {
      await action();
      setMessage(success);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const runEvaluate = () =>
    run(async () => {
      await apiClient.post(`/jobs/${jobId}/evaluate`);
      await reload();
    }, "Hodnocení dokončeno.");

  const runResponse = () =>
    run(async () => {
      const res = await apiClient.post<GeneratedResponse>(`/jobs/${jobId}/generate-response`);
      setResponseText(res.content);
      setDrafts((d) => [res, ...d]);
    }, "Návrh reakce připraven – před odesláním ho zkontrolujte a upravte.");

  const trackApplication = () =>
    run(async () => {
      await apiClient.post(`/applications/from-job/${jobId}`);
      await loadApplication();
    }, "Žádost založena v evidenci.");

  const changeStatus = (status: string) =>
    run(async () => {
      if (!application) return;
      await apiClient.patch(`/applications/${application.id}/status`, { status, note: "" });
      await loadApplication();
    }, "Stav žádosti uložen.");

  function addNote(e: FormEvent) {
    e.preventDefault();
    run(async () => {
      if (!application) return;
      await apiClient.post(`/applications/${application.id}/notes`, { body: noteText });
      setNoteText("");
      await loadApplication();
    }, "Poznámka uložena.");
  }

  async function copyDraft() {
    try {
      await navigator.clipboard.writeText(responseText);
      setMessage("Text zkopírován do schránky.");
    } catch {
      setError("Kopírování se nezdařilo – označte text ručně.");
    }
  }

  const latest = evaluations[0];
  const href = job?.url ? safeHref(job.url) : null;

  if (!job) {
    return error ? <p className="error" role="alert">{error}</p> : <p>Načítání…</p>;
  }

  return (
    <div className="grid">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>{job.title}</h1>
          <p className="muted">{job.company || "zaměstnavatel neuveden"} · {job.location || "lokalita neuvedena"}</p>
          {href && <a href={href} target="_blank" rel="noopener noreferrer">Otevřít inzerát</a>}
        </div>
        <div className="row">
          <button className="btn" type="button" onClick={runEvaluate} disabled={busy}>AI hodnocení</button>
          <button className="btn secondary" type="button" onClick={runResponse} disabled={busy}>Návrh reakce</button>
          {!application && (
            <button className="btn secondary" type="button" onClick={trackApplication} disabled={busy}>Založit žádost</button>
          )}
        </div>
      </div>
      {message && <p className="muted" role="status">{message}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {job.duplicate_of_id && (
        <p className="error">Možná duplicita k <Link to={`/jobs/${job.duplicate_of_id}`}>nabídce #{job.duplicate_of_id}</Link></p>
      )}

      {latest && (
        <section className="card grid">
          <h2>AI hodnocení · <span className="score-pill">{latest.score}</span></h2>
          <p>{latest.summary}</p>
          <List title="Důvody" items={latest.reasons} />
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
            <List title="Výhody" items={latest.pros} />
            <List title="Nedostatky" items={latest.cons} />
            <List title="Požadované dovednosti z profilu" items={latest.required_skills} />
            <List title="Výhodou (z profilu)" items={latest.preferred_skills} />
          </div>
          <List title="Rizika" items={latest.risks} />
          <p className="muted">
            Poskytovatel: {latest.provider} · {new Date(latest.created_at).toLocaleString("cs-CZ")}
            {evaluations.length > 1 && ` · celkem hodnocení: ${evaluations.length}`}
          </p>
        </section>
      )}

      {responseText && (
        <section className="card grid">
          <h2>Návrh reakce (draft)</h2>
          <textarea aria-label="Návrh reakce" rows={12} value={responseText} onChange={(e) => setResponseText(e.target.value)} />
          <div className="row">
            <button className="btn secondary" type="button" onClick={copyDraft}>Zkopírovat</button>
            {drafts[0]?.recommended_cv_version && (
              <span className="muted">Doporučená verze CV: {drafts[0].recommended_cv_version}</span>
            )}
          </div>
          <p className="muted">
            Nic se neodesílá automaticky. Úpravy v poli se neukládají – zkopírujte text po kontrole. Uložených návrhů: {drafts.length}.
          </p>
        </section>
      )}

      {application && (
        <section className="card grid">
          <h2>Evidence žádosti</h2>
          <label>
            Stav
            <select value={application.status} onChange={(e) => changeStatus(e.target.value)} disabled={busy}>
              {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <div>
            <strong>Historie</strong>
            <ul>
              {history.map((h) => (
                <li key={h.id}>
                  {new Date(h.created_at).toLocaleString("cs-CZ")}: {h.from_status ? `${APPLICATION_STATUS_LABELS[h.from_status] || h.from_status} → ` : ""}
                  {APPLICATION_STATUS_LABELS[h.to_status] || h.to_status}
                  {h.note && ` (${h.note})`}
                </li>
              ))}
            </ul>
          </div>
          <form className="grid" onSubmit={addNote}>
            <textarea aria-label="Nová poznámka" placeholder="Poznámka (např. termín pohovoru)" rows={3} value={noteText} onChange={(e) => setNoteText(e.target.value)} required />
            <button className="btn secondary" type="submit" disabled={busy}>Přidat poznámku</button>
          </form>
          {notes.length > 0 && (
            <ul>
              {notes.map((n) => (
                <li key={n.id}>
                  <span className="muted">{new Date(n.created_at).toLocaleString("cs-CZ")}</span> – {n.body}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="card">
        <h2>Text inzerátu</h2>
        <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}>{job.raw_text || "Bez textu"}</pre>
      </section>
    </div>
  );
}

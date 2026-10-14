import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiClient, errorText } from "../api";
import LinkifiedText from "../components/LinkifiedText";
import { safeHref } from "../utils/safeUrl";
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
  const [snoozeNote, setSnoozeNote] = useState("");
  const [snoozeDays, setSnoozeDays] = useState(7);
  const [dismissNote, setDismissNote] = useState("");
  const [appSnoozeNote, setAppSnoozeNote] = useState("");
  const [appSnoozeDays, setAppSnoozeDays] = useState(7);
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
    setResponseText((current) => {
      const fromApi = rs[0]?.content || "";
      if (!fromApi) return current;
      // staré uložené návrhy někdy obsahovaly JSON z LLM; po opravě API vrací čistý text
      if (!current || current.trimStart().startsWith("{")) return fromApi;
      return current;
    });
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
  const snoozedActive =
    job?.inbox_status === "snoozed" && job?.snoozed_until && new Date(job.snoozed_until) > new Date();
  const isDismissed = job?.inbox_status === "dismissed";

  function submitSnooze(e: FormEvent) {
    e.preventDefault();
    run(async () => {
      await apiClient.post(`/jobs/${jobId}/snooze`, { note: snoozeNote.trim(), days: snoozeDays });
      setSnoozeNote("");
      await reload();
    }, "Nabídka odložena.");
  }

  function submitDismiss(e: FormEvent) {
    e.preventDefault();
    run(async () => {
      await apiClient.post(`/jobs/${jobId}/dismiss`, { note: dismissNote.trim() });
      setDismissNote("");
      await reload();
    }, "Nabídka zamítnuta – najdete ji v záložce Zamítnuté.");
  }

  const restoreInbox = () =>
    run(async () => {
      await apiClient.post(`/jobs/${jobId}/restore-inbox`);
      await reload();
    }, "Nabídka je znovu mezi aktivními.");

  const appSnoozedActive =
    application?.next_action_at && new Date(application.next_action_at) > new Date();

  function submitAppSnooze(e: FormEvent) {
    e.preventDefault();
    if (!application) return;
    run(async () => {
      await apiClient.post(`/applications/${application.id}/snooze`, {
        note: appSnoozeNote.trim(),
        days: appSnoozeDays,
      });
      setAppSnoozeNote("");
      await loadApplication();
    }, "Žádost odložena – najdete ji v záložce Odložené.");
  }

  const restoreAppSnooze = () =>
    run(async () => {
      if (!application) return;
      await apiClient.post(`/applications/${application.id}/restore-snooze`);
      await loadApplication();
    }, "Odložení žádosti zrušeno.");

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

      <section className="card grid">
        <h2>Rozhodnutí o nabídce</h2>
        {snoozedActive && (
          <p className="muted">
            Odloženo do {new Date(job.snoozed_until!).toLocaleString("cs-CZ")}
            {job.snooze_note && <> – <em>{job.snooze_note}</em></>}
          </p>
        )}
        {isDismissed && (
          <p className="muted">
            Zamítnuto {job.dismissed_at ? new Date(job.dismissed_at).toLocaleString("cs-CZ") : ""}
            {job.dismissed_note && <> – <em>{job.dismissed_note}</em></>}
          </p>
        )}
        {(snoozedActive || isDismissed) && (
          <button className="btn secondary" type="button" onClick={restoreInbox} disabled={busy}>
            Vrátit mezi aktivní
          </button>
        )}
        {!isDismissed && (
          <form className="grid" onSubmit={submitSnooze}>
            <h3>Odložit</h3>
            <label>
              Délka
              <select value={snoozeDays} onChange={(e) => setSnoozeDays(Number(e.target.value))} disabled={busy}>
                <option value={3}>3 dny</option>
                <option value={7}>7 dní</option>
                <option value={14}>14 dní</option>
                <option value={30}>30 dní</option>
              </select>
            </label>
            <label>
              Proč odložit? (povinné)
              <textarea
                rows={2}
                value={snoozeNote}
                onChange={(e) => setSnoozeNote(e.target.value)}
                placeholder="např. čekám na výsledek jiného pohovoru"
                required
                minLength={3}
                disabled={busy}
              />
            </label>
            <button className="btn secondary" type="submit" disabled={busy}>Odložit nabídku</button>
          </form>
        )}
        {!isDismissed && (
          <form className="grid" onSubmit={submitDismiss}>
            <h3>Zamítnout</h3>
            <label>
              Proč ne? (povinné)
              <textarea
                rows={2}
                value={dismissNote}
                onChange={(e) => setDismissNote(e.target.value)}
                placeholder="např. nízký plat, špatná lokalita"
                required
                minLength={3}
                disabled={busy}
              />
            </label>
            <button className="btn secondary" type="submit" disabled={busy}>Zamítnout nabídku</button>
          </form>
        )}
      </section>

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
          {appSnoozedActive && (
            <p className="muted">
              Odloženo do {new Date(application.next_action_at!).toLocaleString("cs-CZ")}
              {application.snooze_note && <> – <em>{application.snooze_note}</em></>}
            </p>
          )}
          {appSnoozedActive ? (
            <button className="btn secondary" type="button" onClick={restoreAppSnooze} disabled={busy}>
              Zrušit odložení žádosti
            </button>
          ) : (
            <form className="grid" onSubmit={submitAppSnooze}>
              <h3>Odložit žádost</h3>
              <label>
                Délka
                <select value={appSnoozeDays} onChange={(e) => setAppSnoozeDays(Number(e.target.value))} disabled={busy}>
                  <option value={3}>3 dny</option>
                  <option value={7}>7 dní</option>
                  <option value={14}>14 dní</option>
                  <option value={30}>30 dní</option>
                </select>
              </label>
              <label>
                Proč odložit? (povinné)
                <textarea
                  rows={2}
                  value={appSnoozeNote}
                  onChange={(e) => setAppSnoozeNote(e.target.value)}
                  placeholder="např. čekám na odpověď jinde"
                  required
                  minLength={3}
                  disabled={busy}
                />
              </label>
              <button className="btn secondary" type="submit" disabled={busy}>Odložit žádost</button>
            </form>
          )}
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

      <section className="card grid">
        <h2>Text inzerátu</h2>
        <div style={{ whiteSpace: "pre-wrap" }}>
          {job.raw_text ? <LinkifiedText text={job.raw_text} /> : "Bez textu"}
        </div>
        {href && (
          <p>
            <a href={href} target="_blank" rel="noopener noreferrer">Originální nabídka</a>
          </p>
        )}
      </section>
    </div>
  );
}

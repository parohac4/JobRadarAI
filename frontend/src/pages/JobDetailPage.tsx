import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiClient } from "../api";
import type { Evaluation, JobListing } from "../types";

export default function JobDetailPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const [job, setJob] = useState<JobListing | null>(null);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [responseText, setResponseText] = useState("");
  const [message, setMessage] = useState("");

  const reload = async () => {
    const j = await apiClient.get<JobListing>(`/jobs/${jobId}`);
    setJob(j);
    const ev = await apiClient.get<Evaluation[]>(`/jobs/${jobId}/evaluations`);
    setEvaluations(ev);
  };

  useEffect(() => {
    reload();
  }, [jobId]);

  async function runEvaluate() {
    setMessage("");
    await apiClient.post(`/jobs/${jobId}/evaluate`);
    await reload();
    setMessage("Hodnocení dokončeno.");
  }

  async function runResponse() {
    setMessage("");
    const res = await apiClient.post<{ content: string }>(`/jobs/${jobId}/generate-response`);
    setResponseText(res.content);
    setMessage("Návrh reakce připraven – upravte před odesláním.");
  }

  async function trackApplication() {
    await apiClient.post(`/applications/from-job/${jobId}`);
    setMessage("Žádost založena v evidenci.");
  }

  const latest = evaluations[0];

  return (
    <div className="grid">
      {!job ? (
        <p>Načítání…</p>
      ) : (
        <>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <div>
              <h1>{job.title}</h1>
              <p className="muted">{job.company} · {job.location || "lokalita neuvedena"}</p>
              {job.url && <a href={job.url} target="_blank" rel="noreferrer">Otevřít inzerát</a>}
            </div>
            <div className="row">
              <button className="btn" type="button" onClick={runEvaluate}>AI hodnocení</button>
              <button className="btn secondary" type="button" onClick={runResponse}>Návrh reakce</button>
              <button className="btn secondary" type="button" onClick={trackApplication}>Evidence žádosti</button>
            </div>
          </div>
          {message && <p className="muted">{message}</p>}
          {job.duplicate_of_id && <p className="error">Možná duplicita k nabídce #{job.duplicate_of_id}</p>}

          {latest && (
            <section className="card grid">
              <h2>AI hodnocení · <span className="score-pill">{latest.score}</span></h2>
              <p>{latest.summary}</p>
              <div><strong>Důvody</strong><ul>{latest.reasons.map((r) => <li key={r}>{r}</li>)}</ul></div>
              <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
                <div><strong>Výhody</strong><ul>{latest.pros.map((r) => <li key={r}>{r}</li>)}</ul></div>
                <div><strong>Nedostatky</strong><ul>{latest.cons.map((r) => <li key={r}>{r}</li>)}</ul></div>
              </div>
              {latest.risks.length > 0 && <div><strong>Rizika</strong><ul>{latest.risks.map((r) => <li key={r}>{r}</li>)}</ul></div>}
              <p className="muted">Poskytovatel: {latest.provider}</p>
            </section>
          )}

          {responseText && (
            <section className="card grid">
              <h2>Návrh reakce (draft)</h2>
              <textarea rows={12} value={responseText} onChange={(e) => setResponseText(e.target.value)} />
              <p className="muted">Odeslání e-mailem zatím není automatické – zkopírujte text po kontrole.</p>
            </section>
          )}

          <section className="card">
            <h2>Text inzerátu</h2>
            <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}>{job.raw_text || "Bez textu"}</pre>
          </section>
        </>
      )}
    </div>
  );
}

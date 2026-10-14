import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient, errorText } from "../api";
import { APPLICATION_STATUS_LABELS, type Application } from "../types";

type AppInbox = "active" | "snoozed";

function isSnoozed(a: Application): boolean {
  return Boolean(a.next_action_at && new Date(a.next_action_at) > new Date());
}

export default function ApplicationsPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [inbox, setInbox] = useState<AppInbox>("active");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [snoozeTarget, setSnoozeTarget] = useState<Application | null>(null);
  const [snoozeNote, setSnoozeNote] = useState("");
  const [snoozeDays, setSnoozeDays] = useState(7);

  const reload = useCallback(() => {
    const qs = inbox === "snoozed" ? "?inbox=snoozed" : "";
    return apiClient
      .get<Application[]>(`/applications${qs}`)
      .then(setApps)
      .catch((err) => setError(errorText(err)));
  }, [inbox]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function changeStatus(app: Application, status: string) {
    setError("");
    try {
      await apiClient.patch(`/applications/${app.id}/status`, { status, note: "" });
      await reload();
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function restoreSnooze(app: Application) {
    setBusy(true);
    setError("");
    try {
      await apiClient.post(`/applications/${app.id}/restore-snooze`);
      await reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  function submitSnooze(e: FormEvent) {
    e.preventDefault();
    if (!snoozeTarget) return;
    setBusy(true);
    setError("");
    apiClient
      .post(`/applications/${snoozeTarget.id}/snooze`, { note: snoozeNote.trim(), days: snoozeDays })
      .then(async () => {
        setSnoozeTarget(null);
        setSnoozeNote("");
        await reload();
      })
      .catch((err) => setError(errorText(err)))
      .finally(() => setBusy(false));
  }

  return (
    <div className="grid">
      <h1>Evidence výběrových řízení</h1>
      {error && <p className="error" role="alert">{error}</p>}

      <section className="card grid">
        <div className="row" style={{ gap: "0.5rem" }}>
          <button
            type="button"
            className={inbox === "active" ? "btn" : "btn secondary"}
            onClick={() => setInbox("active")}
          >
            Aktivní
          </button>
          <button
            type="button"
            className={inbox === "snoozed" ? "btn" : "btn secondary"}
            onClick={() => setInbox("snoozed")}
          >
            Odložené
          </button>
        </div>
        <p className="muted">
          Odložená žádost se po uplynutí termínu znovu zobrazí mezi aktivními. Poznámka vysvětluje důvod odložení.
        </p>
      </section>

      {snoozeTarget && (
        <section className="card grid">
          <h2>Odložit: {snoozeTarget.job_title}</h2>
          <form className="grid" onSubmit={submitSnooze}>
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
                required
                minLength={3}
                disabled={busy}
              />
            </label>
            <div className="row">
              <button className="btn" type="submit" disabled={busy}>Uložit odložení</button>
              <button className="btn secondary" type="button" onClick={() => setSnoozeTarget(null)} disabled={busy}>
                Zrušit
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="card">
        <table>
          <thead>
            <tr>
              <th>Pozice</th>
              <th>Stav</th>
              {inbox === "snoozed" && <th>Do kdy</th>}
              {inbox === "snoozed" && <th>Poznámka</th>}
              <th>Aktualizace</th>
              <th>Akce</th>
            </tr>
          </thead>
          <tbody>
            {apps.map((a) => (
              <tr key={a.id}>
                <td>
                  <Link to={`/jobs/${a.job_listing_id}`}>{a.job_title}</Link>
                  <div className="muted">{a.company}</div>
                </td>
                <td>{APPLICATION_STATUS_LABELS[a.status] || a.status}</td>
                {inbox === "snoozed" && (
                  <td>{a.next_action_at ? new Date(a.next_action_at).toLocaleString("cs-CZ") : "–"}</td>
                )}
                {inbox === "snoozed" && <td>{a.snooze_note || "–"}</td>}
                <td>{new Date(a.updated_at).toLocaleString("cs-CZ")}</td>
                <td>
                  <div className="row" style={{ flexWrap: "wrap", gap: "0.35rem" }}>
                    {inbox === "active" && (
                      <>
                        <button
                          className="btn secondary"
                          type="button"
                          disabled={busy}
                          onClick={() => {
                            setSnoozeTarget(a);
                            setSnoozeNote("");
                          }}
                        >
                          Odložit
                        </button>
                        <select
                          aria-label="Stav žádosti"
                          value={a.status}
                          onChange={(e) => changeStatus(a, e.target.value)}
                        >
                          {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                          ))}
                        </select>
                      </>
                    )}
                    {inbox === "snoozed" && isSnoozed(a) && (
                      <button className="btn secondary" type="button" disabled={busy} onClick={() => restoreSnooze(a)}>
                        Zrušit odložení
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {apps.length === 0 && (
          <p className="muted">
            {inbox === "snoozed"
              ? "Žádné odložené žádosti."
              : "Zatím žádné aktivní žádosti – vytvořte je z detailu nabídky."}
          </p>
        )}
      </section>
    </div>
  );
}

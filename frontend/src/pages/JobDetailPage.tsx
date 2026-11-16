import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { apiClient, errorText } from '../api';
import type { InteractionState, JobNote } from '../aggregate';
import JobNoteEditor from '../components/JobNoteEditor';
import { safeHref } from '../utils/safeUrl';

type Detail = InteractionState & { title: string; company: string; location: string; url: string; raw_text: string; note: JobNote };

export default function JobDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const [job, setJob] = useState<Detail | null>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    setJob(null); setError(''); setSaving(true);
    async function load() {
      try {
        const detail = await apiClient.get<Detail>(`/aggregate/jobs/${id}`);
        if (!active) return;
        setJob(detail);
        try {
          const state = await apiClient.patch<InteractionState>(`/aggregate/jobs/${id}/interaction`, { seen: true });
          if (active) setJob(current => current ? { ...current, seen_at: state.seen_at } : current);
        } catch (e) { if (active) setError('Zobrazení se nepodařilo uložit: ' + errorText(e)); }
      } catch (e) { if (active) setError(errorText(e)); }
      finally { if (active) setSaving(false); }
    }
    void load();
    return () => { active = false; };
  }, [id]);

  async function change(changes: { seen?: boolean; marked?: boolean }) {
    if (!job || saving) return;
    setSaving(true); setError('');
    try {
      const state = await apiClient.patch<InteractionState>(`/aggregate/jobs/${job.id}/interaction`, changes);
      setJob(current => current ? {
        ...current,
        ...(changes.seen !== undefined ? { seen_at: state.seen_at } : {}),
        ...(changes.marked !== undefined ? { marked: state.marked, marked_at: state.marked_at } : {}),
      } : current);
    } catch (e) { setError('Označení se nepodařilo uložit: ' + errorText(e)); }
    finally { setSaving(false); }
  }

  const href = job ? safeHref(job.url) : null;
  return <div className="grid">
    <Link className="text-link" to={`/${location.search}`}>← Zpět na nabídky</Link>
    {error && <p className="error" role="alert">{error}</p>}
    {job ? <article className="card grid">
      <h1>{job.title}</h1><p>{job.company} · {job.location}</p>
      <div className="row">
        {job.seen_at && <span className="seen-tag">Viděno</span>}
        <button className="btn secondary" type="button" disabled={saving} aria-pressed={job.marked} onClick={() => void change({ marked: !job.marked })}>{job.marked ? '★ Označeno' : '☆ Označit nabídku'}</button>
        <button className="btn secondary" type="button" disabled={saving} onClick={() => void change({ seen: !job.seen_at })}>{job.seen_at ? 'Vrátit mezi neviděné' : 'Označit jako viděné'}</button>
      </div>
      {href && <a className="btn detail-original" href={href} target="_blank" rel="noopener noreferrer" onClick={() => { if (!job.seen_at) void change({ seen: true }); }} onAuxClick={e => { if (e.button === 1 && !job.seen_at) void change({ seen: true }); }}>Úplný inzerát na pracovním portálu ↗</a>}
      <p className="muted">Načtený přehled nabídky. Aktuálnost, podrobné požadavky a odpověď najdete na původním portálu.</p>
      <JobNoteEditor key={job.id} jobId={job.id} title={job.title} initialNote={job.note || { text: '', updated_at: null }} expanded onSaved={note => setJob(current => current ? { ...current, note } : current)} />
      <div className="job-text">{job.raw_text}</div>
    </article> : !error && <p>Načítám nabídku…</p>}
  </div>;
}

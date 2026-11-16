import { useEffect, useId, useRef, useState } from 'react';
import { apiClient, errorText } from '../api';
import type { JobNote } from '../aggregate';

type Props = { jobId: number; title: string; initialNote: JobNote; expanded?: boolean; onSaved?: (note: JobNote) => void };

export default function JobNoteEditor({ jobId, title, initialNote, expanded = false, onSaved }: Props) {
  const fieldId = useId();
  const [text, setText] = useState(initialNote.text);
  const [open, setOpen] = useState(expanded);
  const [status, setStatus] = useState<'saved' | 'pending' | 'saving' | 'error'>('saved');
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const latest = useRef(initialNote.text);
  const saved = useRef(initialNote.text);
  const deleteRequested = useRef(false);
  const pending = useRef<Promise<void> | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const alive = useRef(false);
  const flushRef = useRef<() => Promise<void>>(async () => {});
  const onSavedRef = useRef(onSaved);
  onSavedRef.current = onSaved;

  async function flush(): Promise<void> {
    clearTimeout(timer.current);
    if (pending.current) return pending.current;
    if (latest.current === saved.current && !deleteRequested.current) {
      if (alive.current) setStatus('saved');
      return;
    }
    // Serialize saves: a slow response must not restore an older edit or a deleted note.
    const task = async () => {
      try {
        while (latest.current !== saved.current || deleteRequested.current) {
          const value = latest.current;
          const removing = deleteRequested.current;
          deleteRequested.current = false;
          if (alive.current) { setStatus('saving'); setError(''); }
          try {
            const path = `/aggregate/jobs/${jobId}/note`;
            const note = removing
              ? await apiClient.delete<JobNote>(path, { keepalive: true })
              : await apiClient.put<JobNote>(path, { text: value }, { keepalive: true });
            saved.current = note.text;
            if (latest.current === value) {
              latest.current = note.text;
              if (alive.current) setText(note.text);
            }
            if (alive.current) onSavedRef.current?.(note);
          } catch (e) {
            if (alive.current) { setStatus('error'); setError(errorText(e)); }
            return;
          }
        }
        if (alive.current) setStatus('saved');
      } finally { pending.current = null; }
    };
    pending.current = task();
    return pending.current;
  }
  flushRef.current = flush;

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      clearTimeout(timer.current);
      void flushRef.current();
    };
  }, []);

  function edit(value: string) {
    latest.current = value;
    setText(value); setError(''); setStatus(value === saved.current && !pending.current ? 'saved' : 'pending');
    clearTimeout(timer.current);
    timer.current = setTimeout(() => { void flushRef.current(); }, 600);
  }

  async function remove() {
    deleteRequested.current = true;
    latest.current = '';
    setText(''); setDeleting(true);
    try { await flushRef.current(); }
    finally { if (alive.current) setDeleting(false); }
  }

  return <details className="job-note" open={open} onToggle={e => setOpen(e.currentTarget.open)}>
    <summary>{text || saved.current ? 'Poznámka k nabídce' : 'Přidat poznámku'}{!open && text && <span className="note-summary-preview"> · {text.slice(0, 80)}{text.length > 80 ? '…' : ''}</span>}</summary>
    <div className="note-content">
      <label htmlFor={fieldId} className="muted">Vaše poznámka</label>
      <textarea id={fieldId} aria-label={`Poznámka k nabídce ${title}`} rows={3} maxLength={10000}
        value={text} disabled={deleting} onChange={e => edit(e.target.value)} onBlur={() => { void flushRef.current(); }}
        placeholder="Napište si, co si chcete k nabídce zapamatovat…" />
      <div className="note-footer">
        <small className={status === 'error' ? 'error' : 'muted'} role="status" aria-live="polite">
          {status === 'error' ? 'Uložení se nepodařilo. Text zůstává v editoru.' : status === 'saving' || status === 'pending' ? 'Ukládám…' : text ? 'Uloženo automaticky' : 'Změny se ukládají automaticky'}
        </small>
        <div className="row">
          {status === 'error' && <button type="button" className="btn secondary" onClick={() => { void flushRef.current(); }}>Zkusit uložit znovu</button>}
          <button type="button" className="btn secondary note-delete" disabled={deleting || (!text && !saved.current)} onClick={() => { void remove(); }}>{deleting ? 'Mažu…' : 'Smazat poznámku'}</button>
        </div>
      </div>
      {error && <small className="error" role="alert">{error}</small>}
    </div>
  </details>;
}

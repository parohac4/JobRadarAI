import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiClient, errorText } from '../api';
import { safeHref } from '../utils/safeUrl';
import { sourceNames, type InteractionState, type MonitorStatus, type Offer, type OfferList, type SettingsResponse } from '../aggregate';

export default function JobsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedSort = searchParams.get('sort') || '';
  const sort = ['newest', 'oldest', 'distance', 'match'].includes(requestedSort) ? requestedSort : '';
  const source = searchParams.get('source') || '';
  const query = searchParams.get('q') || '';
  const seen = ['unseen', 'seen'].includes(searchParams.get('seen') || '') ? searchParams.get('seen')! : 'all';
  const markedOnly = searchParams.get('marked') === '1';
  const requestedPage = Number(searchParams.get('page') || 0);
  const page = Number.isSafeInteger(requestedPage) && requestedPage >= 0 ? requestedPage : 0;
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [status, setStatus] = useState<MonitorStatus | null>(null);
  const [result, setResult] = useState<OfferList>({ items: [], total: 0, has_more: false });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');
  const [syncStart, setSyncStart] = useState<number | null>(null);
  const [previousRun, setPreviousRun] = useState<number | null>(null);
  const [saving, setSaving] = useState<Set<number>>(new Set());
  const savingRef = useRef(new Set<number>());
  const requestVersion = useRef(0);
  const refreshRef = useRef<() => Promise<unknown>>(async () => {});
  const mountedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; requestVersion.current++; };
  }, []);

  function updateFilters(changes: Record<string, string>) {
    setSearchParams(previous => {
      const next = new URLSearchParams(previous);
      if (!('page' in changes)) next.delete('page');
      for (const [key, value] of Object.entries(changes)) {
        if (value && value !== 'all' && !(key === 'page' && value === '0')) next.set(key, value);
        else next.delete(key);
      }
      return next;
    }, { replace: true });
  }

  const reload = useCallback(async () => {
    if (!mountedRef.current) return null;
    const version = ++requestVersion.current;
    const params = new URLSearchParams({ skip: String(page * 50), limit: '50', q: query, seen });
    if (sort) params.set('sort', sort);
    if (source) params.set('source', source);
    if (markedOnly) params.set('marked_only', 'true');
    try {
      const [jobs, state] = await Promise.all([
        apiClient.get<OfferList>(`/aggregate/jobs?${params}`),
        apiClient.get<MonitorStatus>('/aggregate/status'),
      ]);
      if (version === requestVersion.current) {
        setResult(jobs); setStatus(state); setError('');
        if (page > 0 && jobs.items.length === 0) {
          setSearchParams(previous => {
            const next = new URLSearchParams(previous);
            const lastPage = Math.max(0, Math.ceil(jobs.total / 50) - 1);
            if (lastPage) next.set('page', String(lastPage)); else next.delete('page');
            return next;
          }, { replace: true });
        }
      }
      return state;
    } catch (err) {
      if (version === requestVersion.current) setError(errorText(err));
      return null;
    } finally { if (version === requestVersion.current) setLoading(false); }
  }, [page, query, sort, source, seen, markedOnly, setSearchParams]);
  refreshRef.current = reload;

  useEffect(() => {
    apiClient.get<SettingsResponse>('/aggregate/settings').then(setSettings).catch(e => setError(errorText(e)));
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => { reload(); }, 250);
    return () => { clearTimeout(timer); requestVersion.current++; };
  }, [reload]);
  useEffect(() => {
    const timer = window.setInterval(async () => {
      const state = await reload();
      if (syncStart && state?.last_run && state.last_run.id !== previousRun && new Date(state.last_run.started_at).getTime() >= syncStart - 3000) {
        setBusy(false); setSyncStart(null); setNotice(state.last_run.message);
      } else if (syncStart && Date.now() - syncStart > 240000) {
        setBusy(false); setSyncStart(null); setNotice('Sběr se zatím nepotvrdil. Zkontrolujte stav zdrojů v nastavení.');
      }
    }, busy ? 3000 : 30000);
    return () => clearInterval(timer);
  }, [reload, busy, syncStart, previousRun]);

  async function sync() {
    setBusy(true); setError(''); setNotice(''); setPreviousRun(status?.last_run?.id ?? null); setSyncStart(Date.now());
    try { await apiClient.post('/aggregate/sync'); }
    catch (e) { setError(errorText(e)); setBusy(false); setSyncStart(null); }
  }

  async function changeInteraction(job: Offer, changes: { seen?: boolean; marked?: boolean }) {
    if (savingRef.current.has(job.id)) return;
    savingRef.current.add(job.id); setSaving(new Set(savingRef.current));
    try {
      const state = await apiClient.patch<InteractionState>(`/aggregate/jobs/${job.id}/interaction`, changes);
      if (!mountedRef.current) return;
      requestVersion.current++;
      setResult(previous => ({ ...previous, items: previous.items.map(item => item.id === job.id ? {
        ...item,
        ...(changes.seen !== undefined ? { seen_at: state.seen_at } : {}),
        ...(changes.marked !== undefined ? { marked: state.marked, marked_at: state.marked_at } : {}),
      } : item) }));
      await refreshRef.current();
    } catch (e) { if (mountedRef.current) setError('Označení se nepodařilo uložit: ' + errorText(e)); }
    finally { savingRef.current.delete(job.id); if (mountedRef.current) setSaving(new Set(savingRef.current)); }
  }

  async function recordClick(job: Offer) {
    if (job.seen_at) return;
    // A link must still record its click while a bookmark save is in flight.
    try {
      const state = await apiClient.patch<InteractionState>(`/aggregate/jobs/${job.id}/interaction`, { seen: true });
      if (!mountedRef.current) return;
      requestVersion.current++;
      setResult(previous => ({ ...previous, items: previous.items.map(item => item.id === job.id ? { ...item, seen_at: state.seen_at } : item) }));
      await refreshRef.current();
    } catch (e) { if (mountedRef.current) setError('Zobrazení se nepodařilo uložit: ' + errorText(e)); }
  }
  const config = settings?.settings;
  const filtered = seen !== 'all' || markedOnly || Boolean(query) || Boolean(source);
  const detailSearch = searchParams.toString() ? `?${searchParams}` : '';

  return <div className="grid aggregate-page">
    <header className="page-heading"><div><p className="eyebrow">VAŠE PRÁCE NA JEDNOM MÍSTĚ</p><h1>Pracovní nabídky</h1><p className="muted">Vyberte si práci. Procházení portálů nechte na hlídači.</p></div>
      <button className="btn" disabled={busy} onClick={sync}>{busy ? 'Probíhá sběr…' : 'Načíst nové nabídky'}</button></header>
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p className="info" role="status">{notice}</p>}
    <section className="search-summary card"><div><span className="eyebrow">KDE HLEDÁME</span><h2>{config?.city || 'Načítání…'} <span className="muted">+ {config?.radius_km ?? '–'} km</span></h2>
      <p>{config?.keywords || 'Všechny profese'}{config?.ai_enabled ? ' · AI preference zapnuté' : ''}</p>
      <p className="muted">{config?.sources.map(x => sourceNames[x]).join(' · ')}{config?.custom_feeds.some(f => f.enabled) ? ' · vlastní RSS' : ''}</p></div>
      <div className="summary-meta"><span className={`status-dot ${status?.monitoring_enabled ? 'on' : ''}`}></span>{status?.monitoring_enabled ? `Hlídání každých ${status.interval_minutes} min` : 'Pravidelné hlídání pozastavené'}
      <small className="muted">{status?.last_run?.finished_at ? `Poslední kontrola ${new Date(status.last_run.finished_at).toLocaleString('cs-CZ')}` : 'První kontrola ještě neproběhla'}</small>
      <Link className="text-link" to="/settings">Upravit hledání a zdroje →</Link></div></section>
    {status && !status.settings_current && <p className="info">Nové nastavení se použije při příštím sběru. Můžete jej spustit hned tlačítkem nahoře.</p>}
    {settings && !settings.worker_enabled && <p className="error">Pravidelný sběr je na serveru vypnutý.</p>}
    {status?.last_run?.details.ai_error && <p className="info">{status.last_run.details.ai_error}</p>}
    {Object.values(status?.last_run?.details.sources || {}).some(s => s.status !== 'ok') && <p className="info">Některé zdroje se nepodařilo načíst celé. <Link className="text-link" to="/settings">Zobrazit stav zdrojů →</Link></p>}
    <section className="results-toolbar" aria-label="Filtry nabídek">
      <strong>{result.total} nabídek{filtered ? ' po filtrování' : ' v okolí'}</strong>
      <div className="row">
        <input aria-label="Hledat v nabídkách" placeholder="Hledat v nabídkách…" value={query} onChange={e => updateFilters({ q: e.target.value })} />
        <select aria-label="Pracovní portál" value={source} onChange={e => updateFilters({ source: e.target.value })}>
          <option value="">Všechny zdroje</option>{config?.sources.map(s => <option value={s} key={s}>{sourceNames[s]}</option>)}
          {config?.custom_feeds.some(f => f.enabled) && <option value="custom">Vlastní RSS</option>}
        </select>
        <select aria-label="Viděné nabídky" value={seen} onChange={e => updateFilters({ seen: e.target.value })}>
          <option value="all">Viděné i neviděné</option><option value="unseen">Skrýt viděné</option><option value="seen">Jen viděné</option>
        </select>
        <select aria-label="Řazení nabídek" title="Stáří podle prvního načtení nabídky" value={sort || config?.sort || 'newest'} onChange={e => updateFilters({ sort: e.target.value })}>
          <option value="newest">Od nejnovějších</option><option value="oldest">Od nejstarších</option><option value="distance">Nejmenší vzdálenost</option><option value="match">Největší shoda s preferencemi</option>
        </select>
        <label className="check-label marked-filter"><input type="checkbox" checked={markedOnly} onChange={e => updateFilters({ marked: e.target.checked ? '1' : '' })} />Pouze označené</label>
        {filtered && <button className="btn secondary" onClick={() => updateFilters({ q: '', source: '', seen: '', marked: '' })}>Zrušit filtry</button>}
      </div>
    </section>
    <p className="muted fine-print">Otevření detailu nebo původního inzerátu nabídku označí jako viděnou. Hvězdičkou si ji můžete samostatně označit.</p>
    {loading ? <p role="status">Načítám nabídky…</p> : result.items.length === 0 ? <section className="card empty-state">
      <h2>{filtered ? 'Žádná nabídka pro zvolené filtry' : 'Zatím žádná nabídka pro toto hledání'}</h2>
      <p className="muted">{filtered ? 'Zkuste zobrazit také viděné nabídky nebo zrušte ostatní filtry.' : 'Spusťte sběr, rozšiřte okruh nebo upravte klíčová slova.'}</p>
      {filtered ? <button className="btn secondary" onClick={() => updateFilters({ q: '', source: '', seen: '', marked: '' })}>Zrušit filtry</button> : <Link className="btn secondary" to="/settings">Upravit hledání</Link>}
    </section> : <div className="offer-list">{result.items.map(job => {
      const href = safeHref(job.url);
      return <article className={`card offer${job.seen_at ? ' is-seen' : ''}`} key={job.id}>
        <div className="offer-main"><div className="offer-tags">
          <span className="source-tag">{sourceNames[job.source] || 'Vlastní RSS'}</span>
          <span className="muted">Načteno {new Date(job.imported_at).toLocaleDateString('cs-CZ')}</span>
          {job.seen_at && <span className="seen-tag" title={`Poprvé zobrazeno ${new Date(job.seen_at).toLocaleString('cs-CZ')}`}>Viděno</span>}
          {job.marked && <span className="marked-tag">★ Označeno</span>}
        </div>
          <h2><Link to={`/jobs/${job.id}${detailSearch}`} onClick={() => void recordClick(job)} onAuxClick={e => { if (e.button === 1) void recordClick(job); }}>{job.title}</Link></h2>
          <p className="company">{job.company || 'Zaměstnavatel neuveden'}</p>
          <p className="muted">{job.location || 'Místo práce neuvedeno'} · {job.distance_km !== null ? `${job.distance_km} km` : job.remote ? 'Na dálku / celá ČR' : 'Vzdálenost neznámá'}</p>
          <p className="offer-preview">{job.summary || job.preview}</p>
        </div>
        <div className="offer-action">
          {job.score !== null && <div className="match-score"><strong>{job.score}%</strong><small>{job.score_kind === 'ai' ? 'AI shoda' : 'Shoda slov'}</small></div>}
          {config?.ai_enabled && job.score_kind !== 'ai' && <small className="muted">Čeká na AI hodnocení</small>}
          <div className="offer-controls">
            <button type="button" className="btn secondary" aria-pressed={job.marked} disabled={saving.has(job.id)} onClick={() => void changeInteraction(job, { marked: !job.marked })}>{job.marked ? '★ Označeno' : '☆ Označit'}</button>
            <button type="button" className="btn secondary" disabled={saving.has(job.id)} onClick={() => void changeInteraction(job, { seen: !job.seen_at })}>{job.seen_at ? 'Vrátit mezi neviděné' : 'Označit jako viděné'}</button>
            {href && <a className="btn secondary" href={href} target="_blank" rel="noopener noreferrer" onClick={() => recordClick(job)} onAuxClick={e => { if (e.button === 1) recordClick(job); }}>Otevřít inzerát ↗</a>}
          </div>
        </div>
      </article>;
    })}</div>}
    {(page > 0 || result.has_more) && <nav className="row" aria-label="Stránky nabídek">
      <button className="btn secondary" disabled={page === 0} onClick={() => updateFilters({ page: String(page - 1) })}>Předchozí</button><span>Strana {page + 1}</span>
      <button className="btn secondary" disabled={!result.has_more} onClick={() => updateFilters({ page: String(page + 1) })}>Další</button>
    </nav>}
    <footer className="muted fine-print">Vzdálenost je vzdušnou čarou od středu obce. Zobrazujeme nabídky načtené za posledních 30 dní; dostupnost ověřte na původním portálu. Zdroje: pracovní portály, <a href="https://sitprace.cz/pro-vyvojare" target="_blank" rel="noreferrer">Síť práce (CC BY 4.0)</a> a <a href="https://www.geonames.org/" target="_blank" rel="noreferrer">GeoNames (CC BY 4.0)</a>.</footer>
  </div>;
}

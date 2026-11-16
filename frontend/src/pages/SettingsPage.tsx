import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient, errorText } from '../api';
import type { MonitorStatus, SearchSettings, SettingsResponse } from '../aggregate';

export default function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [form, setForm] = useState<SearchSettings | null>(null);
  const [places, setPlaces] = useState<{ label: string }[]>([]);
  const [status, setStatus] = useState<MonitorStatus | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [feedTitle, setFeedTitle] = useState('');
  const [feedUrl, setFeedUrl] = useState('');
  useEffect(() => {
    Promise.all([apiClient.get<SettingsResponse>('/aggregate/settings'), apiClient.get<MonitorStatus>('/aggregate/status')])
      .then(([d, s]) => { setData(d); setForm(d.settings); setStatus(s); }).catch(e => setError(errorText(e)));
  }, []);
  useEffect(() => {
    if (!form?.city) { setPlaces([]); return; }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiClient.get<{ items: { label: string }[] }>(`/aggregate/places?q=${encodeURIComponent(form.city)}`)
        .then(d => { if (!controller.signal.aborted) setPlaces(d.items); }).catch(() => {});
    }, 250);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [form?.city]);
  function update<K extends keyof SearchSettings>(key: K, value: SearchSettings[K]) {
    setForm(old => old ? { ...old, [key]: value } : old); setMessage('');
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('');
    try {
      const d = await apiClient.put<{ settings: SearchSettings }>('/aggregate/settings', form);
      setForm(d.settings); setMessage('Hledání uloženo. Spouštím sběr podle nového nastavení…');
      try { await apiClient.post('/aggregate/sync'); }
      catch (e) { setMessage('Hledání je uložené. Ruční sběr se nepodařilo spustit: ' + errorText(e)); }
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  if (!form || !data) return <div><h1>Nastavení hledání</h1>{error ? <p role="alert" className="error">{error}</p> : <p>Načítám nastavení…</p>}</div>;
  return <div className="grid settings-page"><header><p className="eyebrow">HLÍDAČ PRÁCE</p><h1>Nastavení hledání</h1><p className="muted">Kde hledat, co vás baví a které portály průběžně sledovat.</p></header>
    {error && <p className="error" role="alert">{error}</p>}{message && <p className="info" role="status">{message} <Link className="text-link" to="/">Zobrazit nabídky →</Link></p>}
    <form className="grid" onSubmit={save}>
      <section className="card grid"><h2>1. Místo a okruh</h2><div className="settings-columns"><label>Obec / město<input list="places" autoComplete="off" required value={form.city} onChange={e => update('city', e.target.value)} placeholder="Začněte psát název obce…" /><datalist id="places">{places.map(p => <option key={p.label} value={p.label} />)}</datalist><small className="muted">Vyberte obec z našeptávače. Stejnojmenná sídla rozlišují souřadnice.</small></label>
      <label>Okruh od obce (km)<input type="number" required min={1} max={500} value={form.radius_km} onChange={e => update('radius_km', Number(e.target.value))} /></label></div>
      <label className="check-label"><input type="checkbox" checked={form.include_remote} onChange={e => update('include_remote', e.target.checked)} />Zahrnout práci na dálku a celostátní nabídky bez určené obce</label>
      <label className="check-label"><input type="checkbox" checked={form.include_unknown} onChange={e => update('include_unknown', e.target.checked)} />Zahrnout i nabídky s neznámou lokalitou</label><small className="muted">Hybridní práce se filtruje podle místa dojíždění. Práce na dálku se zahrne, pokud ji zdroj ve výsledcích poskytne.</small></section>
      <section className="card grid"><h2>2. Jakou práci hledat</h2><label>Pozice nebo klíčová slova<input value={form.keywords} maxLength={300} onChange={e => update('keywords', e.target.value)} placeholder="Např. technik, účetní, Linux…" /><small className="muted">Prázdné pole = všechny profese. Stačí shoda alespoň jednoho slova.</small></label>
      <label className="check-label"><input type="checkbox" checked={form.ai_enabled} onChange={e => update('ai_enabled', e.target.checked)} />Hledat a řadit také podle AI preferencí</label>
      {form.ai_enabled && <><label>Co by vás bavilo a čemu se chcete vyhnout<textarea rows={5} required maxLength={4000} value={form.ai_preferences} onChange={e => update('ai_preferences', e.target.value)} placeholder="Baví mě opravovat techniku, pomáhat lidem a hledat řešení. Hledám denní směny, nechci aktivní prodej ani noční provoz." /></label>
        <p className="muted">AI posoudí načtené nabídky podle vašeho popisu a vysvětlí jejich vhodnost. Nové i dosud nevyhodnocené nabídky prochází postupně, maximálně {data.ai_daily_limit} hodnocení denně. Po změně přání se skóre přepočítá. AI dostane tento popis a text nabídky.</p>
        {!data.ai_available && <p className="info">AI zatím není na serveru připojená. Preference můžete uložit; sběr funguje i bez AI, hodnocení bude dostupné po připojení.</p>}</>}
      <div className="settings-columns"><label>Výchozí řazení<select value={form.sort} onChange={e => update('sort', e.target.value as SearchSettings['sort'])}><option value="newest">Nejnovější</option><option value="distance">Nejbližší</option><option value="match">Největší shoda s preferencemi</option></select></label><label>Minimální shoda (%)<input type="number" required min={0} max={100} value={form.min_score} onChange={e => update('min_score', Number(e.target.value))} /><small className="muted">0 = všechny. Vyšší limit skryje i dosud nevyhodnocené nabídky.</small></label></div></section>
      <section className="card grid"><h2>3. Pracovní portály</h2><p className="muted">Vybrané zdroje hlídač načítá automaticky. Stejné nabídky slučuje.</p><div className="source-grid">{data.sources.map(s => {
        const state = status?.last_run?.details.sources?.[s.id];
        return <div className="source-card" key={s.id}><label className="check-label"><input type="checkbox" checked={form.sources.includes(s.id)} onChange={e => update('sources', e.target.checked ? [...form.sources, s.id] : form.sources.filter(x => x !== s.id))} /><strong>{s.name}</strong></label><p className="muted">{s.description}</p><a className="text-link" href={s.url} target="_blank" rel="noreferrer">Otevřít portál ↗</a>{state && <div className="source-state"><span className={state.status === 'ok' ? 'success' : 'error'}>{state.status === 'ok' ? `Načteno · ${state.found ?? 0} nabídek` : state.status === 'partial' ? 'Načteno částečně' : 'Načtení selhalo'}</span><small className="muted">{new Date(state.checked_at).toLocaleString('cs-CZ')}</small>{state.last_success_at && <small className="muted">Poslední úspěšné načtení: {new Date(state.last_success_at).toLocaleString('cs-CZ')}</small>}{state.error && <small className="error">{state.error}</small>}</div>}</div>;
      })}</div><p className="muted fine-print">Sběr probíhá z veřejných seznamů, RSS a API. Portály mohou měnit rozhraní nebo omezit přístup. Hlídač prochází postupně omezený počet stránek; úplnost všech nabídek nelze zaručit. Síť práce vrací nejvýše 50 výsledků na dotaz.</p>
      <h3>Další zdroje RSS / Atom</h3>{form.custom_feeds.map((f, i) => <div className="custom-feed" key={i}><label className="check-label"><input type="checkbox" checked={f.enabled} onChange={e => update('custom_feeds', form.custom_feeds.map((v, n) => n === i ? { ...v, enabled: e.target.checked } : v))} />{f.title}</label><small className="muted">{f.url}</small><button className="btn secondary" type="button" onClick={() => update('custom_feeds', form.custom_feeds.filter((_, n) => n !== i))}>Odebrat</button></div>)}
      {form.custom_feeds.length < 10 && <div className="feed-add"><label>Název zdroje<input value={feedTitle} maxLength={100} onChange={e => setFeedTitle(e.target.value)} placeholder="Např. kariérní RSS firmy" /></label><label>Veřejná URL RSS / Atom<input value={feedUrl} onChange={e => setFeedUrl(e.target.value)} placeholder="https://…/rss" /></label><button className="btn secondary" type="button" disabled={!feedTitle.trim() || !/^https?:\/\//.test(feedUrl)} onClick={() => { update('custom_feeds', [...form.custom_feeds, { title: feedTitle.trim(), url: feedUrl.trim(), enabled: true }]); setFeedTitle(''); setFeedUrl(''); }}>Přidat zdroj</button></div>}
      </section>
      <section className="card grid"><h2>4. Pravidelné sledování</h2><label className="check-label"><input type="checkbox" checked={form.monitoring_enabled} onChange={e => update('monitoring_enabled', e.target.checked)} />Automaticky sledovat nabídky i při zavřené nástěnce</label><label>Jak často<select value={form.interval_minutes} onChange={e => update('interval_minutes', Number(e.target.value))}>{[15, 30, 60, 180, 360, 720, 1440].map(v => <option key={v} value={v}>{v < 60 ? `Každých ${v} minut` : v === 1440 ? 'Jednou denně' : `Každých ${v / 60} hodin`}</option>)}</select></label>{!data.worker_enabled && <p className="error">Worker je na serveru vypnutý; automatické sledování nyní neběží.</p>}</section>
      <div className="save-bar"><button className="btn" type="submit" disabled={busy}>{busy ? 'Ukládám…' : 'Uložit a hledat nabídky'}</button><Link className="text-link" to="/">Zpět na nabídky</Link></div>
    </form>
  </div>;
}

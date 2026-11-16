import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiClient, errorText } from '../api';
import { safeHref } from '../utils/safeUrl';
export default function JobDetailPage() {
  const { id } = useParams();
  const [job, setJob] = useState<{title: string; company: string; location: string; url: string; raw_text: string} | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { apiClient.get<NonNullable<typeof job>>(`/aggregate/jobs/${id}`).then(setJob).catch(e => setError(errorText(e))); }, [id]);
  const href = job ? safeHref(job.url) : null;
  return <div className="grid"><Link className="text-link" to="/">← Zpět na nabídky</Link>{error && <p className="error" role="alert">{error}</p>}{job ? <article className="card grid"><h1>{job.title}</h1><p>{job.company} · {job.location}</p>{href && <a className="btn detail-original" href={href} target="_blank" rel="noopener noreferrer">Úplný inzerát na pracovním portálu ↗</a>}<p className="muted">Načtený přehled nabídky. Aktuálnost, podrobné požadavky a odpověď najdete na původním portálu.</p><div className="job-text">{job.raw_text}</div></article> : !error && <p>Načítám nabídku…</p>}</div>;
}

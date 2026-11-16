export type SearchSettings = {
  city: string; radius_km: number; keywords: string; ai_enabled: boolean; ai_preferences: string;
  sources: string[]; custom_feeds: { title: string; url: string; enabled: boolean }[];
  monitoring_enabled: boolean; interval_minutes: number; include_remote: boolean; include_unknown: boolean;
  sort: 'match' | 'distance' | 'newest'; min_score: number;
};
export type Source = { id: string; name: string; description: string; url: string };
export type SettingsResponse = { settings: SearchSettings; sources: Source[]; ai_available: boolean; worker_enabled: boolean; ai_daily_limit: number };
export type Offer = { id: number; title: string; company: string; location: string; url: string; source: string;
  imported_at: string; distance_km: number | null; remote: boolean; score: number | null;
  score_kind: 'ai' | 'keywords' | null; summary: string; preview: string };
export type OfferList = { items: Offer[]; total: number; has_more: boolean };
export type SourceStatus = { name: string; status: string; found?: number; created?: number; error: string; checked_at: string; last_success_at?: string | null };
export type MonitorStatus = { monitoring_enabled: boolean; interval_minutes: number; settings_current: boolean;
  last_run: { id: number; status: string; started_at: string; finished_at: string | null; message: string;
    details: { sources: Record<string, SourceStatus>; created: number; evaluated: number; ai_error?: string } } | null };
export const sourceNames: Record<string, string> = { jobs: 'Jobs.cz', prace: 'Prace.cz', sitprace: 'Síť práce / ÚP', kariera: 'Kariera.cz', custom: 'Vlastní zdroj' };

export type JobListing = {
  id: number;
  title: string;
  company: string;
  location: string;
  url: string;
  source: string;
  raw_text: string;
  availability: string;
  duplicate_of_id: number | null;
  imported_at: string;
  latest_score: number | null;
  requirements_text?: string;
  evaluations_count?: number;
};

export type Evaluation = {
  id: number;
  job_listing_id: number;
  score: number;
  summary: string;
  reasons: string[];
  required_skills: string[];
  preferred_skills: string[];
  pros: string[];
  cons: string[];
  risks: string[];
  provider: string;
  created_at: string;
};

export type Application = {
  id: number;
  job_listing_id: number;
  status: string;
  updated_at: string;
  job_title?: string;
  company?: string;
};

export type ApplicationHistory = {
  id: number;
  from_status: string | null;
  to_status: string;
  note: string;
  created_at: string;
};

export type ApplicationNote = {
  id: number;
  body: string;
  created_at: string;
};

export type GeneratedResponse = {
  id: number;
  job_listing_id: number;
  response_type: string;
  content: string;
  recommended_cv_version: string;
  provider: string;
  created_at: string;
};

export type DashboardStats = {
  total_jobs: number;
  open_jobs: number;
  applications_active: number;
  recommended_count: number;
  avg_score: number | null;
};

export type Profile = {
  id: number;
  user_id: number;
  summary: string;
  skills: string[];
  experience: Record<string, unknown>[];
  education: Record<string, unknown>[];
  preferences: Record<string, unknown>;
  cv_versions: Record<string, unknown>[];
};

export const APPLICATION_STATUS_LABELS: Record<string, string> = {
  new_offer: "Nová nabídka",
  recommended: "Doporučená",
  response_ready: "Připravená reakce",
  sent: "Odesláno",
  waiting: "Čeká na odpověď",
  interview: "Pohovor",
  rejected: "Zamítnuto",
  accepted: "Přijato",
  archived: "Archivováno",
};

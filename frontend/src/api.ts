import { withBase } from "./config";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";
const TOKEN_KEY = "jobradar_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

function detailMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d?.msg === "string" ? d.msg : JSON.stringify(d)))
      .join("; ");
  }
  return fallback;
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    setToken(null);
    window.location.href = withBase("/login");
    throw new ApiError("Přihlášení vypršelo", 401);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(detailMessage(body, `Chyba API (${res.status})`), res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(detailMessage(data, "Přihlášení se nezdařilo"), res.status);
  }
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export function errorText(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export const apiClient = {
  get: <T>(path: string) => api<T>(path),
  post: <T>(path: string, body?: unknown) =>
    api<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
};

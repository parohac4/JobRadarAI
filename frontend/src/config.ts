/** Cesta pod doménou, např. /nastenka (bez koncového lomítka). V dev prázdné = kořen. */
export const BASE_PATH = (import.meta.env.VITE_BASE_PATH || "/").replace(/\/$/, "") || "";

export function withBase(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!BASE_PATH || BASE_PATH === "/") return p;
  return `${BASE_PATH}${p}`;
}

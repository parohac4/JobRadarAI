/** Povolí jen http/https – stejná logika jako u odkazu „Otevřít inzerát“. */
export function safeHref(url: string): string | null {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.href : null;
  } catch {
    return null;
  }
}

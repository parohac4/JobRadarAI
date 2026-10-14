# Changelog

## 0.3.0 – Automatizace a etapa 2

- Worker (`python -m app.worker`) + služba v `deploy/docker-compose.apache.yml`
- Gmail IMAP import job alertů, RSS zdroje v DB (`/feeds`), ruční sync v Nastavení
- Výchozí feedy Síť práce (JSON API), import nabídek včetně lokality
- Po importu volitelné auto-hodnocení a notifikace (e-mail / Telegram)
- Import CV (PDF/DOCX) do profilu (`POST /profile/cv`)
- HttpOnly cookie přihlášení, endpoint `/auth/logout`, volitelný `ENFORCE_CLOUDFLARE`
- **Filtr a řazení nabídek podle vzdálenosti** od domovského města v profilu – [docs/08-LOKALITA-A-VZDALENOST.md](docs/08-LOKALITA-A-VZDALENOST.md)
- AI: modely GPT-5 bez parametru `temperature`; průvodní dopis jako čistý text (ne JSON); hodnocení respektuje `from`/`to` u zkušeností
- UI: klikatelné odkazy na originální inzerát, linkifikace URL v textu nabídky
- Odložení a zamítnutí nabídky s povinnou poznámkou; záložky Aktivní / Odložené / Zamítnuté
- Odložení žádosti se poznámkou (Evidence výběrových řízení + detail nabídky)
- Nastavení: zapínání/vypínání jednotlivých RSS/API zdrojů (sloupec `enabled`)
- Výchozí RSS Kariera.cz (ČR + Jihočeský + hardware), Aktuální nabídky práce, Práce pro OZP – doplnění při startu
- Silnější deduplikace nabídek mezi zdroji (název+firma, podobný titul); duplicity se neukládají znovu a v seznamu jsou skryté
- Dokumentace [docs/07-ETAPA2-PLAN.md](docs/07-ETAPA2-PLAN.md)

## 0.2.0 – Code review: bezpečnost, opravy, UI

Detail všech nálezů: [docs/06-CODE-REVIEW.md](docs/06-CODE-REVIEW.md).

- Bezpečnost: ochrana importu URL proti SSRF, limit neúspěšných přihlášení (429), kontrola `SECRET_KEY`
  v produkci, ohraničení textu inzerátu proti prompt injection, CORS jen pro vývoj, Swagger v produkci
  vypnutý, backend bez roota, bezpečnostní hlavičky a CSP, gitleaks v CI
- Opravy: padající CI (lifespan v testech), falešné duplicity z fuzzy shody, URL s query parametry,
  poslední skóre a průměr, mock a šablona dopisu už nevymýšlí požadavky ani zkušenosti
- UI: detail nabídky zobrazuje uložené návrhy, stav, historii a poznámky žádosti; editovatelný profil;
  audit log v Nastavení; srozumitelné chyby a odhlášení po vypršení tokenu
- API: `GET /jobs?sort=score&min_score=`, `GET /jobs/{id}/responses`, `GET /applications/by-job/{id}`,
  `GET /applications/{id}/notes`, `GET /system/audit`; health 503 bez DB, demo reset 403 mimo demo
- Nasazení: Apache rozdělen na společný include + vhosty shodné se serverem, healthcheck DB,
  odstraněn ukázkový `index.html`, který by přepsal osobní web
- Nové proměnné: `ACCESS_TOKEN_EXPIRE_MINUTES` (výchozí 24 h), `LOGIN_MAX_FAILURES`,
  `LOGIN_WINDOW_SECONDS`, `API_DOCS`

## 0.1.3 – Odkaz na osobní web

- README odkazuje na repozitář `chcetejelena-web`

## 0.1.2 – Dokumentace repozitáře

- `docs/05-OBSAH-REPozITARE.md` – co patří do gitu, osobní web mimo JobRadarAI
- Upřesnění deploy dokumentace (kořen domény vs `/nastenka`)

## 0.1.1 – Dokumentace a produkce chcetejelena.cz

- Dokumentace: DNS Cloudflare, Apache + Docker deploy, přístupy `.env`, provoz a zálohy
- Produkční stack `deploy/docker-compose.apache.yml`, cesta `/nastenka`
- Synchronizace `ADMIN_EMAIL` / `ADMIN_PASSWORD` s DB při startu backendu

## 0.1.0 – MVP (Etapa 1)

- Docker Compose (PostgreSQL, FastAPI, React, Caddy)
- Ruční přidání nabídky, import URL a parsování e-mailových upozornění
- Detekce duplicit (URL hash, obsah, fuzzy shoda)
- AI hodnocení 0–100 s vysvětlením (OpenAI volitelně, výchozí mock)
- Návrh reakce (draft) bez automatického odeslání
- Evidence žádostí se stavy a historií
- Profesní profil s výchozími preferencemi (Jihočeský kraj / IT podpora)
- Demo režim s fiktivními daty a omezeným zápisem
- Automatizované testy (pytest, GitHub Actions)

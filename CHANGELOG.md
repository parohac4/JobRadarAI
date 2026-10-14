# Changelog

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

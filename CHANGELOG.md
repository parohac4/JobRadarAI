# Changelog

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

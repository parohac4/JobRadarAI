# JobRadar AI

**Repozitář:** [github.com/parohac4/JobRadarAI](https://github.com/parohac4/JobRadarAI)

[English README](./README.en.md)

Automatizace hledání zaměstnání: sběr inzerátů, AI hodnocení vhodnosti, návrhy reakcí a evidence výběrových řízení. Projekt je open-source (MIT) a připravený jako portfolio ukázka.

**Produkční příklad:** [chcetejelena.cz/nastenka](https://chcetejelena.cz/nastenka/) (přihlášení pod `/nastenka/login`).

Osobní web na kořeni domény: [github.com/parohac4/chcetejelena-web](https://github.com/parohac4/chcetejelena-web).

## Dokumentace

Kompletní návod (DNS, nasazení, přístupy, provoz):

| Dokument | Téma |
|----------|------|
| [docs/README.md](./docs/README.md) | Přehled všech dokumentů |
| [docs/01-DNS-CLOUDFLARE.md](./docs/01-DNS-CLOUDFLARE.md) | Cloudflare Proxied, chyba 521 |
| [docs/02-DEPLOY-VPS.md](./docs/02-DEPLOY-VPS.md) | Apache + Docker na Debian VPS |
| [docs/03-PRISTUPY-A-KONFIGURACE.md](./docs/03-PRISTUPY-A-KONFIGURACE.md) | **`.env`, přihlášení, změna hesla/e-mailu** |
| [docs/04-PROVOZ-A-OBNOVA.md](./docs/04-PROVOZ-A-OBNOVA.md) | Docker příkazy, zálohy, TLS |
| [docs/05-OBSAH-REPozITARE.md](./docs/05-OBSAH-REPozITARE.md) | Co je v gitu / co ne |
| [docs/06-CODE-REVIEW.md](./docs/06-CODE-REVIEW.md) | Code review 0.2.0 – nálezy, opravy, známá omezení |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Architektura a datový model |

## Problém

Hledání práce na více portálech je časově náročné. JobRadar AI centralizuje nabídky, porovnává je s vaším profilem, vysvětluje skóre a pomáhá připravit reakci – **bez automatického odesílání** bez vašeho souhlasu.

## Funkce (MVP – Etapa 1)

- Dashboard se statistikami
- Ruční přidání nabídky, import z URL, vložení těla e-mailového upozornění
- Detekce duplicit napříč záznamy
- AI hodnocení 0–100 + důvody, výhody, rizika (OpenAI volitelně, jinak transparentní heuristika „mock“)
- Návrh motivačního textu (draft)
- Evidence žádostí – stavy, historie a poznámky přímo v detailu nabídky
- Profesní profil s editovatelnými lokalitami, rolemi, zkušenostmi a verzemi CV
- Audit log (přihlášení, importy, hodnocení) v Nastavení
- Světlý / tmavý režim UI
- Demo režim s fiktivními daty

## Architektura

| Komponenta | Technologie |
|------------|-------------|
| API | Python 3.12, FastAPI, OpenAPI |
| DB | PostgreSQL 16 |
| UI | React 18, TypeScript, Vite |
| Produkce | Apache (TLS) + Docker; dev: Caddy v `docker-compose.yml` |
| AI | `AI_PROVIDER=openai` nebo `mock` |

## Rychlý start (lokální vývoj)

```bash
cp .env.example .env
# Upravte ADMIN_PASSWORD a SECRET_KEY
docker compose up --build
```

Aplikace: [http://localhost:8080](http://localhost:8080)  
Přihlášení: hodnoty `ADMIN_EMAIL` / `ADMIN_PASSWORD` z `.env`.

## Produkce na vlastní doméně

1. DNS (Cloudflare) → [docs/01-DNS-CLOUDFLARE.md](./docs/01-DNS-CLOUDFLARE.md)
2. Nasazení → [docs/02-DEPLOY-VPS.md](./docs/02-DEPLOY-VPS.md)
3. Přístupy → [docs/03-PRISTUPY-A-KONFIGURACE.md](./docs/03-PRISTUPY-A-KONFIGURACE.md)

```bash
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml up -d --build
```

## Demo režim

```env
DEMO_MODE=true
```

Při prvním startu s prázdnou DB se fiktivní data naplní automaticky. Obnovení: **Nastavení → Obnovit demo data**
nebo `POST /api/v1/system/demo/reset` (mimo demo režim vrací 403).

## Konfigurace AI

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## Testy

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest tests -q   # unit testy; integrační se bez PostgreSQL přeskočí
```

Integrační testy proti dočasné DB: [docs/04-PROVOZ-A-OBNOVA.md](./docs/04-PROVOZ-A-OBNOVA.md#testy).

## Bezpečnost a soukromí

- Do gitu nepatří `.env`, CV, e-maily ani export DB.
- Produkční hesla pouze na serveru v `.env`.
- Panel není na `/admin`, ale na konfigurovatelné cestě (např. `/nastenka`), s `noindex`.
- Limit neúspěšných přihlášení, ochrana importu URL proti SSRF, oddělení textu inzerátu od instrukcí AI
  (prompt injection), kontrola síly `SECRET_KEY` v produkci, backend v kontejneru bez roota.
- CI skenuje celou historii gitu na uniklá tajemství (gitleaks).
- Podrobnosti a známá omezení: [docs/06-CODE-REVIEW.md](./docs/06-CODE-REVIEW.md).

## Licence

MIT – viz [LICENSE](./LICENSE).

## Roadmap

- **Etapa 2:** import CV (PDF/DOCX), pokročilé reakce
- **Etapa 3:** scheduler, RSS/API, IMAP
- **Etapa 4:** další hardening, screenshoty do README

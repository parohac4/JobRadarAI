# JobRadar AI

**Repozitář:** [github.com/parohac4/JobRadarAI](https://github.com/parohac4/JobRadarAI)

[English README](./README.en.md)

Automatizace hledání zaměstnání: sběr inzerátů, AI hodnocení vhodnosti, návrhy reakcí a evidence výběrových řízení. Projekt je open-source (MIT) a připravený jako portfolio ukázka.

## Problém

Hledání práce na více portálech je časově náročné. JobRadar AI centralizuje nabídky, porovnává je s vaším profilem, vysvětluje skóre a pomáhá připravit reakci – **bez automatického odesílání** bez vašeho souhlasu.

## Funkce (MVP – Etapa 1)

- Dashboard se statistikami
- Ruční přidání nabídky, import z URL, vložení těla e-mailového upozornění
- Detekce duplicit napříč záznamy
- AI hodnocení 0–100 + důvody, výhody, rizika (OpenAI volitelně, jinak mock)
- Návrh motivačního textu (draft)
- Evidence žádostí a změn stavu
- Profesní profil s editovatelnými preferencemi
- Světlý / tmavý režim UI
- Demo režim s fiktivními daty

## Architektura

Viz [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

| Komponenta | Technologie |
|------------|-------------|
| API | Python 3.12, FastAPI, OpenAPI |
| DB | PostgreSQL 16 |
| UI | React 18, TypeScript, Vite |
| Proxy | Caddy |
| AI | Konfigurovatelný LLM (`AI_PROVIDER=openai` nebo `mock`) |

## Rychlý start (Docker)

```bash
cp .env.example .env
# Upravte ADMIN_PASSWORD a SECRET_KEY
docker compose up --build
```

Aplikace: [http://localhost:8080](http://localhost:8080)  
API dokumentace: [http://localhost:8080/api/v1/docs](http://localhost:8080/api/v1/docs) (přes backend port 8000 v dev: `http://localhost:8000/docs` pokud mapujete backend)

Výchozí přihlášení dle `.env` (`ADMIN_EMAIL` / `ADMIN_PASSWORD`).

## Demo režim

```env
DEMO_MODE=true
```

- Pouze fiktivní data, zápis omezen (kromě resetu dema v Nastavení).
- Funguje bez placeného AI API.
- Oddělte od produkce (jiná DB, jiné `.env`).

Obnovení dat: **Nastavení → Obnovit demo data** nebo `POST /api/v1/system/demo/reset`.

## Konfigurace AI

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Bez klíče zůstane **mock** – deterministická heuristika podle profilu (vhodné pro demo a CI).

## Testy

```bash
cd backend
pip install -r requirements.txt
pytest tests/test_dedup.py tests/test_email_parse.py -q

# Integrační testy (běžící PostgreSQL)
export DATABASE_URL=postgresql+asyncpg://jobradar:jobradar_secret@localhost:5432/jobradar
pytest tests/test_api.py -q
```

## Bezpečnost a soukromí

- Do repozitáře nepatří CV, e-maily, hesla ani produkční DB.
- Používejte `.env` a `env.example`.
- Inzeráty a e-maily se považují za nedůvěryhodný vstup (ochrana proti prompt injection v AI vrstvě).
- Produkční nasazení: HTTPS, silná hesla, zálohy `jobradar_pg` volume.

## Portfolio (krátký popis)

**JobRadar AI** – full-stack aplikace (FastAPI + PostgreSQL + React) pro sledování pracovních nabídek s AI skóringem a workflow žádostí. Modulární import zdrojů, deduplikace, audit log, demo režim bez tajných údajů, CI testy.

## Licence

MIT – viz [LICENSE](./LICENSE).

## Roadmap

- **Etapa 2:** import CV (PDF/DOCX), pokročilé reakce
- **Etapa 3:** scheduler, RSS/API dle podmínek portálů, IMAP
- **Etapa 4:** produkční hardening, screenshoty, Debian VPS guide

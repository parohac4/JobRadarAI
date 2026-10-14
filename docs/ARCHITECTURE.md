# JobRadar AI – architektura

## Přehled

JobRadar AI je modulární monorepo: **FastAPI** (REST + OpenAPI), **PostgreSQL**, **React/TypeScript** SPA, **worker** pro plánované úlohy. **Dev:** Caddy v Docker Compose. **Produkce (chcetejelena.cz):** Apache (Let's Encrypt) + reverse proxy na Docker – viz [02-DEPLOY-VPS.md](./02-DEPLOY-VPS.md).

```
                    ┌─────────────┐
                    │   Caddy     │
                    └──────┬──────┘
           /api/*          │          /*
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌──────────────┐          ┌──────────────┐
       │   Backend    │          │   Frontend   │
       │   FastAPI    │          │   React      │
       └──────┬───────┘          └──────────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌────────┐ ┌──────┐ ┌──────────┐
│Postgres│ │Worker│ │ LLM API  │
└────────┘ └──────┘ │ (volitelné)│
                  └──────────┘
```

## Moduly backendu

| Modul | Odpovědnost |
|-------|-------------|
| `auth` | JWT, bcrypt, jeden tenant (MVP: jeden uživatel z env) |
| `jobs` | CRUD nabídek, import URL/text, stav dostupnosti |
| `sources` | Konfigurace zdrojů (RSS, e-mail, ruční) |
| `dedup` | Hash URL + fuzzy shoda titul/zaměstnavatel |
| `profile` | Profesní profil, preference, verze CV (metadata) |
| `ai` | Hodnocení 0–100, vysvětlení; `mock` bez API klíče |
| `geo` | Města ČR (souřadnice), haversine, filtr/řazení nabídek podle vzdálenosti |
| `feeds` / `rss_import` / `sitprace_import` / `imap_import` | Zdroje nabídek, synchronizace |
| `worker` | Plánovaný sync IMAP a RSS |
| `applications` | Stavy žádostí, historie, poznámky |
| `responses` | Návrhy reakcí (MVP: generování textu) |
| `email_import` | Parsování job alert e-mailů (IMAP volitelné) |
| `audit` | Audit log důležitých operací |
| `demo` | Seed fiktivních dat, read-only režim |

## Datový model (MVP)

- **users** – přihlášení
- **job_listings** – pozice, zaměstnavatel, lokalita, text, URL, zdroj, hash
- **job_listing_status** – open/closed/unknown
- **professional_profiles** – preference, shrnutí, dovednosti (JSON)
- **ai_evaluations** – skóre, vysvětlení, povinné/preferované požadavky
- **applications** – vazba na listing, stav, termíny
- **application_history** – změny stavu
- **application_notes** – poznámky uživatele
- **generated_responses** – návrhy textů (draft)
- **sync_runs** – log synchronizací / importů
- **feed_sources** – RSS / JSON URL zdroje uživatele
- **import_state** – např. poslední IMAP UID
- **notification_sent** – odeslané upozornění na vysoké skóre
- **audit_events**

V `professional_profiles.preferences` mohou být `home_city`, `home` (lat/lon), `max_distance_km` – viz [08-LOKALITA-A-VZDALENOST.md](./08-LOKALITA-A-VZDALENOST.md).

## Bezpečnost

- Tajné hodnoty pouze v `.env` (nikdy v gitu); v produkci backend odmítne start se slabým `SECRET_KEY`.
- Přihlášení: bcrypt, JWT (24 h), limit neúspěšných pokusů na e-mail i IP (`core/rate_limit.py`),
  konstantní doba odpovědi i pro neexistující účet, audit `auth.login` / `auth.login_failed`.
- Import URL (`services/job_import.py`): jen http/https, všechny IP cílového hostu musí být veřejné
  (blokace localhost, privátních sítí, metadata cloudu), redirecty ručně s kontrolou každého kroku, max. 2 MB.
- Prompt injection: text inzerátu/e-mailu je v promptu ohraničen `<<<INZERAT>>> … <<<KONEC>>>`
  a systémová instrukce říká, že obsah uvnitř jsou data, ne pokyny. Výstup LLM se normalizuje
  (`normalize_evaluation`) – chybějící nebo špatné typy nerozbijí API.
- AI si nevymýšlí: mock i šablona dopisu pracují jen s dovednostmi z profilu, které se v inzerátu skutečně
  vyskytují; LLM má v instrukci zákaz doplňovat neuvedené zkušenosti.
- Demo režim: `DEMO_MODE=true` – zápis omezen, data se naplní automaticky, žádné IMAP.
- Produkce: HTTPS přes Apache (nebo Caddy), bezpečnostní hlavičky + CSP, Swagger vypnutý, kontejner
  backendu bez roota, CORS jen pro lokální vývoj, zálohy DB (dokumentováno).
- Detail nálezů a známých omezení: [06-CODE-REVIEW.md](./06-CODE-REVIEW.md).

## Rozšíření (Etapa 2+)

- Plné CV PDF/DOCX parse, více verzí souborů.
- Scheduler pro RSS/API zdroje dle ToS.
- IMAP párování odpovědí zaměstnavatelů.

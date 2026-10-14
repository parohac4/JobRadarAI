# Co je a co není v GitHub repozitáři JobRadarAI

## V repozitáři **je** (veřejné)

- Zdrojový kód backendu (`backend/`) a frontendu (`frontend/`)
- Docker Compose (vývoj + produkční varianty v `deploy/`, `docker-compose*.yml`)
- Apache vzor pro proxy na `/nastenka` (`deploy/apache/chcetejelena.conf`)
- Dokumentace (`docs/`, `README.md`, `CHANGELOG.md`)
- Šablona konfigurace [`.env.example`](../.env.example) **bez** skutečných hesel
- CI workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
- Licence MIT

## V repozitáři **není** (záměrně)

| Položka | Kde zůstává |
|---------|-------------|
| `.env` s hesly a API klíči | pouze na serveru / lokálně |
| `.env.credentials-once` | lokální poznámka, v `.gitignore` |
| PostgreSQL data | Docker volume na VPS |
| Nahrané CV, e-maily, osobní poznámky | pouze v DB / soukromých souborech mimo git |
| `backend/.venv/`, `node_modules/` | generuje se při instalaci |

## Osobní web na kořeni domény

Statický web **https://chcetejelena.cz/** (CHCETE JELENA) je **samostatný projekt** mimo tento repozitář:

```text
/home/parohac4/skripty/chcetejelena-web/
```

Na serveru se kopíruje do `/var/www/chcetejelena/`. JobRadar běží jen pod **`/nastenka/`**.

Soubor `deploy/apache/index.html` v JobRadarAI je jen **jednoduchá ukázka** pro první test Apache; produkční úvodní stránku spravuje projekt `chcetejelena-web`.

## Kontrola před `git push`

```bash
git status
git diff
# nesmí být staged: .env, credentials, uploads, zálohy DB
git ls-files | grep -E '^\.env$' && echo 'CHYBA: .env v gitu!' || echo 'OK'
```

## Historie commitů

Smysluplné commity v češtině nebo angličtině; každý push na `main` spouští GitHub Actions (testy).

# Co je a co není v GitHub repozitáři JobRadarAI

## V repozitáři **je** (veřejné)

- Zdrojový kód backendu (`backend/`) a frontendu (`frontend/`)
- Docker Compose (vývoj + produkční varianty v `deploy/`, `docker-compose*.yml`)
- Apache konfigurace pro proxy na `/nastenka` (`deploy/apache/` – shodná s živým serverem)
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

Statický web **https://chcetejelena.cz/** (CHCETE JELENA) je **samostatný repozitář**:

- GitHub: [parohac4/chcetejelena-web](https://github.com/parohac4/chcetejelena-web)
- Lokálně: `/home/parohac4/skripty/chcetejelena-web/`

Na serveru se nasazuje skriptem `deploy.sh` do `/var/www/chcetejelena/` (bez `.git`, README a LICENSE).
JobRadar běží jen pod **`/nastenka/`**. Dřívější ukázkový `deploy/apache/index.html` byl odstraněn,
aby omylem nepřepsal osobní web.

## Kontrola před `git push`

```bash
git status
git diff
# nesmí být staged: .env, credentials, uploads, zálohy DB
git ls-files | grep -E '^\.env$' && echo 'CHYBA: .env v gitu!' || echo 'OK'
```

## Historie commitů

Smysluplné commity v češtině nebo angličtině; každý push na `main` spouští GitHub Actions
(testy backendu, build frontendu a sken tajemství [gitleaks](https://github.com/gitleaks/gitleaks) přes celou historii).

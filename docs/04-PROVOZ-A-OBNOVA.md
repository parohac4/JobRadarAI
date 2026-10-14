# Provoz, Docker a obnova

## Produkční architektura (chcetejelena.cz)

```text
Internet → Cloudflare (Proxied) → Apache :443 (Let's Encrypt)
              → /              → statická úvodní stránka (/var/www/chcetejelena)
              → /nastenka/     → Docker frontend (nginx) :8788
              → /nastenka/api  → Docker backend (FastAPI) :8787
                                    → PostgreSQL (Docker, bez veřejného portu)
```

Soubory:

| Soubor | Účel |
|--------|------|
| [`deploy/docker-compose.apache.yml`](../deploy/docker-compose.apache.yml) | DB + backend + frontend |
| [`deploy/apache/chcetejelena.conf`](../deploy/apache/chcetejelena.conf) | Apache vhost (HTTP) |
| `/etc/apache2/sites-available/chcetejelena-le-ssl.conf` | HTTPS (Certbot) |

---

## Běžné příkazy

Vždy z kořene projektu a **s `--env-file .env`** (jinak chybí `POSTGRES_PASSWORD`):

```bash
cd /home/parohac4/skripty/JobRadar_AI

# Stav kontejnerů
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml ps

# Spuštění / rebuild
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml up -d --build

# Restart jen API (po změně .env přihlášení)
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml restart backend

# Logy
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml logs -f backend
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml logs -f frontend
```

Apache:

```bash
sudo apache2ctl configtest
sudo systemctl reload apache2
```

---

## Health check

```bash
curl -sS https://chcetejelena.cz/nastenka/api/v1/system/health

Po změně frontendu/backendu vždy rebuild **bez cache**, jinak Docker může servírovat starý JS:

```bash
cd /path/to/JobRadar_AI
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml build --no-cache frontend backend worker
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml up -d
```

Ověření: v menu musí být **Zdroje RSS**; `curl -s http://127.0.0.1:8788/assets/index-*.js | grep -q 'Zdroje RSS' && echo OK`
# {"status":"ok","demo_mode":false}
# HTTP 503 {"status":"db_error"} = backend běží, ale nedosáhne na PostgreSQL
```

---

## TLS certifikát (Let's Encrypt)

Certbot na Apache:

```bash
sudo certbot --apache -d chcetejelena.cz -d www.chcetejelena.cz
```

Certifikáty: `/etc/letsencrypt/live/chcetejelena.cz/`  
Obnova: systemd timer `certbot` (automaticky).

Cloudflare: režim **Full (strict)** (origin má platný certifikát).

---

## Záloha PostgreSQL

Zálohy ukládej **mimo repozitář** (např. `~/backups/`, práva 600) – dump obsahuje osobní data.

```bash
cd /home/parohac4/skripty/JobRadar_AI
mkdir -p ~/backups
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > ~/backups/jobradar-$(date +%F-%H%M).sql.gz
chmod 600 ~/backups/*.sql.gz
```

Obnova (pozor, přepíše data):

```bash
gunzip -c ~/backups/jobradar-DATUM.sql.gz | sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml exec -T db \
  psql -U jobradar -d jobradar
```

Docker volume: `deploy_jobradar_pg` (název může být `deploy_jobradar_pg` dle názvu projektu compose).

---

## Testy

Integrační testy potřebují PostgreSQL – **nikdy je nespouštěj proti produkční DB** (vytvářejí data).
Dočasná testovací databáze:

```bash
sudo docker run -d --name jr-test-pg -p 127.0.0.1:55432:5432 \
  -e POSTGRES_USER=jobradar -e POSTGRES_PASSWORD=jobradar_secret -e POSTGRES_DB=jobradar postgres:16-alpine
cd backend
DATABASE_URL=postgresql+asyncpg://jobradar:jobradar_secret@127.0.0.1:55432/jobradar \
  ADMIN_EMAIL=admin@test.local ADMIN_PASSWORD=testpass SECRET_KEY=test .venv/bin/pytest tests -q
sudo docker rm -f jr-test-pg
```

Bez `DATABASE_URL` s PostgreSQL se integrační testy přeskočí a běží jen unit testy.

---

## Lokální vývoj (bez Apache)

```bash
cp .env.example .env
docker compose up --build
```

UI: [http://localhost:8080](http://localhost:8080) (Caddy v `docker-compose.yml`).  
`PUBLIC_PATH` nechte prázdné / kořen – viz `.env.example`.

---

## Řešení problémů

| Příznak | Pravděpodobná příčina | Řešení |
|---------|------------------------|--------|
| Cloudflare **521** | Na origin neběží nic na **443** (Proxied + Full) | Apache SSL + certbot, nebo dočasně Flexible |
| **403** na kořeni domény | Špatný vhost / DocumentRoot | Zkontroluj `chcetejelena.conf` |
| Přihlášení nefunguje, `.env` je „správně“ | DB má jiný e-mail než `.env` | `restart backend` (sync) + tabulka `users` |
| API 502 na `/nastenka` | Backend/frontend neběží | `docker compose ps`, logy backendu |
| `POSTGRES_PASSWORD chybí` při `docker compose` | Zapomenuté `--env-file .env` | Vždy `--env-file .env` |
| Backend nenastartuje, v logu `SECRET_KEY o délce alespoň 32 znaků` | Slabý `SECRET_KEY` při `APP_ENV=production` | `openssl rand -hex 32` → `.env`, restart |
| Přihlášení hlásí „Příliš mnoho neúspěšných pokusů“ (429) | Limit 10 pokusů / 15 min | Počkat, nebo `restart backend` |
| Import URL vrací 400 „interní adresa“ | Ochrana SSRF – URL míří na localhost/privátní síť | Použij veřejnou URL inzerátu |
| `/nastenka/api/v1/docs` vrací 404 | Swagger je v produkci vypnutý | Dočasně `API_DOCS=true` v `.env` + restart |

Apache logy:

```text
/var/log/apache2/chcetejelena-error.log
/var/log/apache2/chcetejelena-access.log
```

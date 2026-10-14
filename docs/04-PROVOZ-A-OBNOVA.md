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
# {"status":"ok","demo_mode":false}
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

```bash
cd /home/parohac4/skripty/JobRadar_AI
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml exec -T db \
  pg_dump -U jobradar jobradar > backup-jobradar-$(date +%F).sql
```

Obnova (pozor, přepíše data):

```bash
cat backup.sql | sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml exec -T db \
  psql -U jobradar -d jobradar
```

Docker volume: `deploy_jobradar_pg` (název může být `deploy_jobradar_pg` dle názvu projektu compose).

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
| Prázdné `POSTGRES_PASSWORD` ve compose | Zapomenuté `--env-file .env` | Vždy `--env-file .env` |

Apache logy:

```text
/var/log/apache2/chcetejelena-error.log
/var/log/apache2/chcetejelena-access.log
```

# Krok 2: Nasazení na VPS (`chcetejelena.cz`)

Předpoklad: DNS podle [01-DNS-CLOUDFLARE.md](./01-DNS-CLOUDFLARE.md).

Na produkci běží **Apache** (TLS + reverse proxy) a **Docker** (PostgreSQL, FastAPI, statický frontend). Alternativa s Caddy na :80/:443 je v [`docker-compose.production.yml`](../docker-compose.production.yml) – na serveru s již běžícím Apache se používá varianta **apache**.

---

## Veřejné URL

| URL | Obsah |
|-----|--------|
| `https://chcetejelena.cz/` | Jednoduchá úvodní HTML stránka |
| `https://chcetejelena.cz/nastenka/` | JobRadar (React SPA) |
| `https://chcetejelena.cz/nastenka/login` | Přihlášení |
| `https://chcetejelena.cz/nastenka/api/v1/...` | REST API |

Cesta **`/nastenka`** je záměrně místo `/admin` (méně nápadná pro roboty). Lze změnit přes `PUBLIC_PATH` v `.env` + rebuild frontendu – viz [03-PRISTUPY-A-KONFIGURACE.md](./03-PRISTUPY-A-KONFIGURACE.md).

---

## 1. Příprava serveru

```bash
sudo apt update
sudo apt install -y docker.io docker-compose certbot python3-certbot-apache
sudo systemctl enable --now docker
```

Firewall (příklad):

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

---

## 2. Klonování a `.env`

```bash
git clone git@github.com:parohac4/JobRadarAI.git
cd JobRadarAI
cp .env.example .env
nano .env
```

Minimální produkční hodnoty:

```env
APP_ENV=production
SECRET_KEY=<dlouhý-náhodný-řetězec>
DEMO_MODE=false

ADMIN_EMAIL=vase@email.cz
ADMIN_PASSWORD=<silné-heslo>

POSTGRES_USER=jobradar
POSTGRES_PASSWORD=<silné-heslo-db>
POSTGRES_DB=jobradar

DOMAIN=chcetejelena.cz
PUBLIC_PATH=/nastenka
```

Přihlášení a synchronizace účtu: [03-PRISTUPY-A-KONFIGURACE.md](./03-PRISTUPY-A-KONFIGURACE.md).

---

## 3. Docker (aplikace)

```bash
cd /home/parohac4/skripty/JobRadar_AI   # nebo vaše cesta
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml up -d --build
```

Kontrola:

```bash
curl -sS http://127.0.0.1:8787/api/v1/system/health
curl -sI http://127.0.0.1:8788/
```

---

## 4. Apache reverse proxy

```bash
sudo mkdir -p /var/www/chcetejelena
sudo cp deploy/apache/index.html /var/www/chcetejelena/
sudo cp deploy/apache/chcetejelena.conf /etc/apache2/sites-available/chcetejelena.conf
sudo a2enmod proxy proxy_http headers rewrite ssl
sudo a2ensite chcetejelena.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

---

## 5. HTTPS (Let's Encrypt)

```bash
sudo certbot --apache -d chcetejelena.cz -d www.chcetejelena.cz \
  --non-interactive --agree-tos -m admin@chcetejelena.cz --redirect
```

V Cloudflare nastav **SSL/TLS → Full (strict)**.

---

## 6. Ověření z internetu

```bash
curl -sS https://chcetejelena.cz/nastenka/api/v1/system/health
```

V prohlížeči: `https://chcetejelena.cz/nastenka/`.

---

## Aktualizace aplikace z gitu

```bash
cd JobRadarAI
git pull
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml up -d --build
```

Provoz a zálohy: [04-PROVOZ-A-OBNOVA.md](./04-PROVOZ-A-OBNOVA.md).

---

## Varianta: pouze Caddy (čistý VPS)

Pokud na serveru **neběží** Apache:

```bash
docker compose -f docker-compose.production.yml up -d --build
```

Viz [`deploy/Caddyfile.production`](../deploy/Caddyfile.production) a proměnné `DOMAIN`, `PUBLIC_PATH`.

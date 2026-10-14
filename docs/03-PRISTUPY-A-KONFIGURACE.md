# Přístupy a konfigurace (`.env`)

Všechna **tajná** a **přihlašovací** nastavení produkce jsou v souboru na serveru:

```text
/cesta/k/JobRadarAI/.env
```

Na serveru `controlhub` typicky:

```text
/home/parohac4/skripty/JobRadar_AI/.env
```

Soubor **nikdy necommituj** do gitu (je v `.gitignore`). V repozitáři je jen šablona [`.env.example`](../.env.example).

---

## Přihlášení do webové aplikace

| Co | Kde |
|----|-----|
| URL přihlášení | `https://<DOMAIN><PUBLIC_PATH>/login` → např. `https://chcetejelena.cz/nastenka/login` |
| E-mail | proměnná `ADMIN_EMAIL` v `.env` |
| Heslo | proměnná `ADMIN_PASSWORD` v `.env` |

Přihlášení řeší **aplikace** (JWT token). Apache ani Cloudflare nemají samostatné HTTP heslo na `/nastenka`.

### Synchronizace účtu s `.env`

Při startu backendu se **jediný uživatel** v databázi synchronizuje s hodnotami `ADMIN_EMAIL` a `ADMIN_PASSWORD` z `.env` (logika v `backend/app/services/bootstrap.py`).

Po změně e-mailu nebo hesla v `.env` **vždy restartuj backend**:

```bash
cd /home/parohac4/skripty/JobRadar_AI
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml restart backend
```

> **Historická poznámka:** Dříve se účet vytvořil jen jednou; změna `ADMIN_EMAIL` v `.env` bez úpravy DB vedla k chybě „Nepodařilo se přihlásit“. To je opraveno synchronizací při startu.

### Zobrazení aktuálních hodnot (na serveru)

```bash
grep -E '^ADMIN_EMAIL=|^ADMIN_PASSWORD=' /home/parohac4/skripty/JobRadar_AI/.env
```

Heslo si **nezapisuj** do chatu ani do screenshotů.

### Ověření účtu v databázi

```bash
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml exec -T db \
  psql -U jobradar -d jobradar -c "SELECT id, email, is_active FROM users;"
```

E-mail ve sloupci `email` musí odpovídat `ADMIN_EMAIL` v `.env` (po restartu backendu).

### Test API přihlášení (na serveru)

```bash
EMAIL=$(grep '^ADMIN_EMAIL=' .env | cut -d= -f2-)
PASS=$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-)
curl -sS -X POST "http://127.0.0.1:8787/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${EMAIL}&password=${PASS}"
```

Očekávaná odpověď: JSON s `access_token`.

---

## Přehled proměnných v `.env`

| Proměnná | Účel |
|----------|------|
| `APP_ENV` | `production` na VPS, `development` lokálně |
| `SECRET_KEY` | Podpis JWT (dlouhý náhodný řetězec) – změna odhlásí všechny session |
| `DEMO_MODE` | `false` na produkci; `true` = demo data, omezený zápis |
| `ADMIN_EMAIL` | Přihlašovací e-mail |
| `ADMIN_PASSWORD` | Přihlašovací heslo |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | PostgreSQL v Dockeru |
| `DATABASE_URL` | Připojení backendu (v Docker compose se často přepisuje) |
| `DOMAIN` | Veřejná doména (`chcetejelena.cz`) |
| `PUBLIC_PATH` | Cesta aplikace bez koncového `/` (`/nastenka`) |
| `AI_PROVIDER` | `mock` nebo `openai` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL` | Volitelné AI API |
| `IMAP_HOST` / `IMAP_USER` / `IMAP_PASSWORD` | Budoucí import e-mailů (Etapa 3) |
| `VITE_API_BASE` / `VITE_BASE_PATH` | Build frontendu – na produkci nastavuje Docker build args |

Kompletní šablona: [`.env.example`](../.env.example).

---

## Co kde **nenastavuješ**

| Místo | Co tam **není** |
|-------|------------------|
| **GitHub** | hesla, `.env`, data z DB |
| **Cloudflare** | přihlášení do JobRadaru (jen DNS + SSL režim) |
| **Apache** | uživatelské účty aplikace (jen reverse proxy + TLS) |
| **Repozitář** | osobní CV, e-maily, produkční DB |

---

## Frontend build a cesta `/nastenka`

Produkční frontend se buildí s:

- `VITE_BASE_PATH=/nastenka/`
- `VITE_API_BASE=/nastenka/api/v1`

Definováno v [`deploy/docker-compose.apache.yml`](../deploy/docker-compose.apache.yml). Po změně `PUBLIC_PATH` je potřeba **přestavět frontend**:

```bash
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml up -d --build frontend
```

---

## Bezpečnostní doporučení

- Silné unikátní `ADMIN_PASSWORD` a `POSTGRES_PASSWORD`.
- `SECRET_KEY` alespoň 32 náhodných bajtů (hex/base64).
- Soubor `.env.credentials-once` (pokud existuje) – jednorázová poznámka hesla při generování; po uložení do `.env` **smaž**.
- Pravidelné zálohy DB – viz [04-PROVOZ-A-OBNOVA.md](./04-PROVOZ-A-OBNOVA.md).

# Etapa 2–3 – plán vývoje

Cíl: automatizovat sběr nabídek (Gmail IMAP + RSS), po importu volitelně vyhodnotit AI a upozornit,
doplnit import CV a zpřísnit přihlášení (HttpOnly cookie). Vše konfigurovatelné v `.env`, bez automatického
odesílání žádostí.

## Pořadí implementace

| Fáze | Obsah | Stav |
|------|--------|------|
| 1 | Worker + `SyncRun`, ruční/spouštěný sync IMAP a RSS | **implementováno v 0.3.0** |
| 2 | UI Nastavení – zdroje RSS (zap/vyp), tlačítka sync, stav IMAP | **implementováno** |
| 3 | Po importu auto-hodnocení + notifikace (e-mail / Telegram) | **implementováno v 0.3.0** |
| 4 | Import CV (PDF/DOCX) do profilu | **implementováno v 0.3.0** |
| 5 | HttpOnly cookie + logout; volitelný lock přes Cloudflare | **implementováno v 0.3.0** |
| 6 | Limity AI (denní strop), veřejná API portálů dle ToS | další iterace |

## Gmail IMAP (doporučené nastavení)

1. V Google účtu zapněte **2FA**.
2. Vytvořte **heslo aplikace** (Google Account → Zabezpečení → Hesla aplikací).
3. Ve Gmailu vytvořte **štítek** např. `JobRadar` a filtr, který do něj posílá upozornění z Jobs.cz / LinkedIn.
4. V `.env`:

```env
IMAP_ENABLED=true
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=vase@gmail.com
IMAP_PASSWORD=heslo-aplikace-16-znaku
IMAP_FOLDER=JobRadar
```

Složka musí odpovídat názvu štítku (Gmail ji mapuje jako `JobRadar` nebo `[Gmail]/JobRadar` – při chybě
zkuste druhou variantu v logu workeru).

## RSS a další zdroje

Zdroje jsou v tabulce `feed_sources` (UI **Zdroje RSS** v menu, cesta `/sources`). Každý zdroj lze **vypnout** přepínačem – vypnuté se při syncu přeskočí (`enabled=false`). Při otevření stránky se doplní chybějící výchozí URL.

| Zdroj | Jak to funguje v JobRadaru |
|-------|----------------------------|
| **Síť práce** ([sitprace.cz](https://sitprace.cz)) | Veřejné JSON API – výchozí vyhledávání pro IT podporu / Linux / Jih (automaticky při prvním startu) |
| **Jobs.cz, Prace.cz** | Veřejné RSS **nemají** – použij **Gmail IMAP** (štítek JobRadar) na e-mailová upozornění |
| **LinkedIn** | Bez RSS – ruční import / e-mail do IMAP |
| **Kariera.cz**, aktualninabidkyprace.cz, praceproozp.cz | Veřejné RSS – výchozí zdroje se doplní při startu backendu (`default_feeds.py`) |
| Klasické **RSS URL** | Lze přidat ručně v Nastavení |

Worker stahuje jen **veřejné** adresy (SSRF ochrana jako u importu z URL).

## Notifikace

```env
NOTIFY_ENABLED=true
NOTIFY_MIN_SCORE=70
NOTIFY_EMAIL_TO=parohac4@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Po nové nabídce s skóre ≥ práh se pošle jedna zpráva (bez opakování pro stejnou nabídku).

## Worker

```bash
# v Dockeru (viz deploy/docker-compose.apache.yml služba worker)
python -m app.worker
```

Interval: `SYNC_INTERVAL_SECONDS` (výchozí 900 = 15 min).

## OpenAI

Beze změny: `AI_PROVIDER=openai` + `OPENAI_API_KEY`. Worker po importu může volat hodnocení, pokud
`AUTO_EVALUATE_ON_IMPORT=true` a není překročen `AI_DAILY_MAX_CALLS`.

## Bezpečnost

- `AUTH_USE_HTTPONLY_COOKIE=true` – token v cookie `jobradar_session` (Secure na produkci).
- `ENFORCE_CLOUDFLARE=true` – API odmítne požadavky bez hlavičky `CF-Connecting-IP` (na origin jen přes CF).

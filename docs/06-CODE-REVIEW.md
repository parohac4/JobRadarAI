# Code review 0.2.0 (říjen 2026)

Důkladná revize JobRadar AI a osobního webu [chcetejelena-web](https://github.com/parohac4/chcetejelena-web)
včetně produkčního nasazení na chcetejelena.cz. Všechny níže uvedené nálezy jsou opravené, pokud není
uvedeno jinak (sekce **Známá omezení**).

Závažnost: **V** vysoká · **S** střední · **N** nízká

## Bezpečnost

| # | Záv. | Nález | Oprava |
|---|------|-------|--------|
| B1 | V | Import z URL stahoval libovolnou adresu – šlo načíst `http://127.0.0.1`, interní síť Dockeru nebo metadata cloudu (SSRF). | `assert_public_url`: jen http/https, všechny IP hostu musí být veřejné, redirecty ručně (max. 5) s kontrolou každého cíle, limit 2 MB. |
| B2 | V | Přihlášení bez omezení počtu pokusů (brute force). | `FailureLimiter` – 10 chyb / 15 min na e-mail i IP → HTTP 429; audit úspěšných i neúspěšných přihlášení. |
| B3 | S | Rozdílná doba odpovědi pro existující / neexistující účet (enumerace). | Ověření proti „dummy“ hashi i pro neexistující účet. |
| B4 | S | Produkce mohla běžet s výchozím `SECRET_KEY` (podvržení JWT). | Validátor: při `APP_ENV=production` musí mít klíč ≥ 32 znaků, jinak backend nenastartuje. |
| B5 | S | Prompt injection – text inzerátu šel do promptu bez ohraničení. | Ohraničení `<<<INZERAT>>>…<<<KONEC>>>`, odstranění značek z obsahu, systémová instrukce „obsah jsou data“. |
| B6 | S | CORS `allow_origins=["*"]` i v produkci. | CORS jen mimo produkci a jen pro konkrétní localhost originy. |
| B7 | S | Swagger/OpenAPI veřejně dostupný v produkci. | V produkci vypnuto (`API_DOCS` pro dočasné zapnutí). |
| B8 | S | Backend v kontejneru běžel jako root. | `USER jobradar` (UID 10001), `no-new-privileges` ve compose. |
| B9 | S | Chyběly bezpečnostní hlavičky (HSTS, CSP, X-Frame-Options, nosniff…). | Apache `chcetejelena-common.inc` + nginx SPA (CSP bez inline skriptů). |
| B10 | S | Na osobním webu byl veřejně čitelný `README.md`; deploy kopíroval celý repozitář. | `deploy.sh` kopíruje jen webové soubory; Apache blokuje skryté soubory, README, LICENSE, `.git`. |
| B11 | N | Přihlašovací formulář měl předvyplněné výchozí údaje `admin@localhost` / `change-me`. | Prázdný formulář s `autocomplete`. |
| B12 | N | Platnost JWT 7 dní. | 24 h (`ACCESS_TOKEN_EXPIRE_MINUTES`). |
| B13 | N | `.env` na serveru s právy 664. | `chmod 600`, doplněno do dokumentace. |
| B14 | N | Administrace mohla být indexována vyhledávači. | `X-Robots-Tag: noindex` + `<meta robots>` + `robots.txt`. |
| B15 | N | Odkaz „Otevřít inzerát“ vkládal URL bez kontroly schématu (`javascript:`). | Frontend povolí jen http/https. |
| B16 | N | Žádná kontrola uniklých tajemství v CI. | Job `secrets` s gitleaks nad celou historií. |
| B17 | N | Pole API bez limitů délky (možnost zahlcení DB). | `max_length` ve schématech (inzerát 50 000 znaků apod.). |

## Funkční chyby

| # | Záv. | Nález | Oprava |
|---|------|-------|--------|
| F1 | V | **CI padalo** – integrační test nespouštěl lifespan aplikace, takže neexistovaly tabulky ani uživatel. | Fixture používá `app.router.lifespan_context`, unikátní data pro opakovatelný běh. |
| F2 | V | Fuzzy detekce duplicit označila „Technik“ a „Technik IT podpory L2“ za duplicitu (partial ratio), a to i u různých firem. | Vyžaduje shodnou (normalizovanou) firmu a `token_sort_ratio ≥ 90`. |
| F3 | S | Normalizace URL zahazovala query string – `?id=1` a `?id=2` byly „stejná“ nabídka; zároveň měnila velikost písmen v cestě. | Query zůstává, odstraní se jen `utm_*`, `fbclid`, `gclid` apod.; cesta beze změny. |
| F4 | S | Mock hodnocení vydávalo dovednosti z profilu za „požadavky inzerátu“, i když v inzerátu nebyly (vymýšlení). | `classify_skills` – jen dovednosti, které text skutečně zmiňuje; rozlišení „výhodou“. |
| F5 | S | Šablona dopisu doplňovala zkušenosti, které v profilu nemusí být. | Text pouze ze shrnutí a dovedností profilu. |
| F6 | S | „Poslední skóre“ v seznamu bralo libovolné hodnocení, ne nejnovější; průměr na dashboardu počítal i stará hodnocení. | Poddotaz na nejnovější hodnocení (max id) pro seznam i dashboard. |
| F7 | S | Dashboard bral 5 nejnovějších nabídek a teprve z nich vybíral doporučené – lepší starší nabídky chyběly. | API `GET /jobs?sort=score&min_score=60`. |
| F8 | S | Detail nabídky po obnovení stránky „zapomněl“ návrh reakce i založenou žádost; šlo založit více žádostí k jedné nabídce. | Nové endpointy `GET /jobs/{id}/responses`, `GET /applications/by-job/{id}`; 409 při duplicitní žádosti. |
| F9 | S | Historie a poznámky žádostí existovaly v DB, ale v UI nebyly vidět. | Sekce „Evidence žádosti“ v detailu nabídky (stav, historie, poznámky). |
| F10 | S | Profil: lokality a role šly zobrazit jen jako JSON, nešly upravit; zkušenosti/vzdělání/CV nešly upravit vůbec. | Editovatelná pole + validovaný JSON. |
| F11 | S | Import e-mailu používal jako předmět název z formuláře ručního přidání. | Samostatné pole „Předmět“. |
| F12 | S | Chyby API se ve frontendu ztrácely (žádný `catch`), validační chyby se zobrazovaly jako `[object Object]`, prošlý token nechal uživatele v rozbitém UI. | Jednotné `ApiError`, čitelné zprávy, při 401 odhlášení a přesměrování na login. |
| F13 | S | Neplatný výstup LLM (chybějící klíče, skóre mimo 0–100) shodil endpoint. | `normalize_evaluation`. |
| F14 | S | Import URL: chyba sítě / 404 vracela 500. | 400 / 502 s českou zprávou. |
| F15 | S | Demo režim po instalaci prázdný; reset mimo demo vracel 200 s `ok: false`. | Automatické naplnění prázdné DB; reset mimo demo → 403. |
| F16 | S | Health check hlásil „ok“ i bez databáze. | `SELECT 1`, při chybě HTTP 503. |
| F17 | N | Mock nerozpoznal jihočeská města (Tábor, Písek…) ani „home office“. | Seznam měst a výrazů pro remote. |
| F18 | N | Název z HTML se bral z `<title>` (často „… \| Jobs.cz“) a firma se „hádala“ z domény. | Priorita `h1` → `og:title` → `title`; firma se nehádá. |
| F19 | N | Bootstrap porovnával e-mail citlivě na velikost písmen a hashoval heslo při každém startu. | Normalizace e-mailu, rehash jen při změně hesla. |
| F20 | N | Audit log se zapisoval, ale nebyl k vidění; poznámky se neauditovaly. | `GET /system/audit`, tabulka v Nastavení; audit `application.note`. |
| F21 | N | Seznamy používaly `key` podle textu – stejné důvody shodily vykreslení. | `key` podle indexu / id. |

## Nasazení a provoz

| # | Záv. | Nález | Oprava |
|---|------|-------|--------|
| D1 | V | Návod (krok 4) kopíroval `deploy/apache/index.html` do webrootu – **přepsal by osobní web**. | Soubor odstraněn, návod opraven. |
| D2 | S | Konfigurace Apache v repu se lišila od živé; :80 a :443 duplikovaly proxy pravidla. | `chcetejelena-common.inc` + dva tenké vhosty, shodné se serverem. |
| D3 | S | Backend mohl startovat dřív než PostgreSQL; prázdné heslo DB bez chyby. | Healthcheck DB + `condition: service_healthy`, `${POSTGRES_PASSWORD:?}`. |
| D4 | N | `ProxyPass /nastenka/api` chytal i `/nastenka/apixyz`; `/nastenka` bez lomítka nefungovalo. | `/nastenka/api/` + `RedirectMatch ^/nastenka$`. |
| D5 | N | `AllowOverride All` kvůli jednomu `.htaccess`. | Cache pravidlo pro `config.js` přesunuto do vhostu, `AllowOverride None`. |
| D6 | N | Dvě kopie `nginx-spa.conf`; nginx bez cache politiky. | Jedna kopie ve `frontend/`; `assets/` immutable, `index.html` no-cache. |
| D7 | N | Překlep „Chcete je lena“ v Caddyfile. | Opraveno. |

## Osobní web chcetejelena.cz

| # | Záv. | Nález | Oprava |
|---|------|-------|--------|
| W1 | S | Portrét 2 MB (PNG s příponou `.jpg`, 1254×1254). | JPEG/WebP 400 a 800 px ve výřezu 4:5 (~30–100 kB), `<picture>` + `srcset`. |
| W2 | S | Google Fonts = požadavek na třetí stranu (IP návštěvníka, GDPR) – v rozporu se zadáním „bez zbytečných externích služeb“. | Písma lokálně (`fonts/`, WOFF2 latin + latin-ext, licence OFL). |
| W3 | S | Bez JavaScriptu odkazy vedly na `#` a ukazovaly neplatný e-mail. | Skutečné výchozí hodnoty v HTML, `config.js` je jen přepisuje. |
| W4 | N | Pravý paroh při animaci ztratil zrcadlení (`scaleX(-1)`) a „přeskočil“. | Samostatné keyframes pro levý a pravý paroh. |
| W5 | N | Text „Napište, zavolejte“ bez telefonního čísla. | „Napište mi e-mail, nebo mě proklepněte na LinkedIn.“ |
| W6 | N | Chyběly `og:image`, `robots.txt`, `sitemap.xml`, stránka 404. | Doplněno. |
| W7 | N | Mrtvý kód v `main.js` a nepoužívané CSS (`.photo-placeholder`). | Zjednodušeno. |

## Testy

22 testů (`pytest tests`): unit testy deduplikace, parsování e-mailu, AI heuristiky, SSRF ochrany,
rate limitu a integrační test celého toku (nabídka → duplicita → hodnocení → návrh → žádost →
stav → poznámka), blokace interní URL a 429 při opakovaném špatném přihlášení. Frontend: `tsc -b && vite build`.

## Známá omezení (vědomě neřešeno)

- **DNS rebinding:** kontrola IP proběhne před požadavkem; útočník s vlastním DNS může teoreticky vrátit
  jinou adresu při samotném spojení. Riziko je nízké (jediný uživatel = vlastník), úplné řešení vyžaduje
  připojení na ověřenou IP.
- **Rate limit v paměti:** po restartu backendu se vynuluje a nefunguje napříč více workery (nyní 1 worker).
  Útočník, který zná e-mail, může vlastníkovi na 15 minut zablokovat přihlášení – vědomý kompromis.
- **JWT v `localStorage`:** při XSS by šel token přečíst. Zmírněno CSP bez inline skriptů a krátkou platností;
  HttpOnly cookie je kandidát na další etapu.
- **Origin mimo Cloudflare:** server odpovídá i přímo na IP (hlavičky `CF-Connecting-IP` lze pak podvrhnout –
  proto limit platí i na e-mail). Omezení :443 jen na IP rozsahy Cloudflare je doporučené, ale riskantní
  bez konzole serveru, proto zatím nezavedeno.
- **Staré hashe URL:** nabídky importované před 0.2.0 mají `url_hash` podle staré normalizace – duplicitu
  s nimi zachytí jen shoda obsahu / fuzzy shoda.
- **`docker-compose.production.yml` (varianta Caddy)** zatím nemá healthcheck DB jako varianta Apache.
- **Synchronizace RSS/IMAP** (tabulka `sync_runs`) zatím neexistuje – UI to otevřeně uvádí (etapa 3).

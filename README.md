# JobRadar — agregátor pracovních nabídek

Aplikace na [chcetejelena.cz/nastenka](https://chcetejelena.cz/nastenka/) soustředí hledání práce do dvou obrazovek: nabídky a nastavení hledání. Přihlášení, hesla a cookies zůstávají stejné.

- Obec z našeptávače (16 tisíc českých sídel), okruh 1–500 km a klíčová slova.
- Výchozí zdroje Jobs.cz, Prace.cz a Síť práce (včetně veřejných nabídek MPSV/Úřadu práce). Volitelně Kariera.cz a až deset vlastních RSS/Atom zdrojů.
- Automatický sběr i při zavřeném webu; nastavitelný interval 15 minut až jeden den, pozastavení a ruční spuštění.
- Řazení od nejnovějších, od nejstarších, podle nejmenší vzdálenosti a shody. Stáří znamená datum prvního načtení. Duplicity se slučují, zdroje lze vypnout.
- Kliknutí na detail či původní inzerát ukládá stav „Viděno“. Hvězdičkou lze nabídku samostatně označit; oba stavy lze zrušit. Filtry skrýt viděné, jen viděné a pouze označené lze kombinovat s dalšími filtry. Stavy jsou v databázi u účtu a přežijí nové načtení i opakovaný import. Filtry seznamu jsou v URL a zachovají se při návratu z detailu.
- Poznámka u každé nabídky, dostupná v seznamu i detailu. Ukládá se automaticky po 600 ms bez psaní a při opuštění pole; lze ji upravit a smazat. Poznámky jsou soukromé pro účet a nepřepisují se importem.
- Volitelné AI preference napsané vlastními slovy; skóre a vysvětlení podle přání uživatele. Původní CV ani staré profesní údaje se pro toto hodnocení nepoužívají. Nový popis zneplatní stará skóre.
- U každého zdroje stav, chyba a poslední úspěšné načtení. Vzdálenost je vzdušnou čarou mezi sídly; nejasná lokalita se nezaměňuje za nulovou vzdálenost. Hybrid se posuzuje podle místa dojíždění.

Původní dashboard, CV/profesní profil, evidence žádostí, odkládání a generování odpovědí nejsou dostupné v UI ani přes původní API. Existující databázové tabulky zůstávají zachované; změna nemaže historická data. Staré odkazy v rozhraní přesměrují na nabídky či nastavení.

## Nasazení existujícího serveru

Připravený upgrade se týká pouze tohoto Compose projektu. Ověří původ kontejnerů, zálohuje pouze databázi JobRadaru a ID původních obrazů, sestaví nové obrazy a nahradí pouze `backend`, `worker`, `frontend` s `--no-deps`. Neregeneruje `.env`, nemění Apache, nepoužívá `down`, nerestartuje PostgreSQL ani ostatní služby.

```bash
cd /home/parohac4/skripty/JobRadar_AI
sudo bash deploy/update-aggregator.sh
```

Vyžaduje skutečná práva správce k Dockeru. Pouhé schválení příkazu v asistentovi nenahradí heslo pro sudo. Zálohy jsou v ignorované složce `.backups/` s omezenými právy.

Tabulky `job_interactions` (viděné a označené nabídky) a `job_notes` (poznámky) vzniknou automaticky při startu backendu. Nevyžaduje ruční úpravu existujících tabulek.

Po nasazení zkontrolujte `/nastenka/api/v1/system/health`, přihlášení, nastavení a první dokončený sběr. Worker musí mít `WORKER_ENABLED=true`. Pro AI platí existující `AI_PROVIDER=openai`, `OPENAI_API_KEY` a `OPENAI_MODEL`; `AI_DAILY_MAX_CALLS` omezuje počet hodnocení (výchozí 50 denně). Bez připojené AI se nabídky normálně sbírají a UI upozorní, že AI hodnocení není dostupné. `AUTO_EVALUATE_ON_IMPORT` a původní IMAP/notifikace nový agregátor nepoužívá.

## Rozsah zdrojů

Výběr pro běžné české hledání staví na Jobs.cz (odborné role), Prace.cz (regionální práce) a Sítí práce (veřejné API/MPSV). Kariera.cz je doplněk, který je ve výchozím stavu vypnutý. Další portály je možné připojit veřejným RSS/Atom zdrojem. Nastavení nevytváří účty ani nezveřejňuje profily na cizích portálech.

Sběr používá veřejné stránky, RSS a API. U Jobs.cz/Prace.cz načítá obec a až čtyři další větší sídla v okruhu, mezi cykly střídá první tři stránky. Při chybějící obecní stránce zkusí regionální adresu a funkční cestu si na 24 hodin zapamatuje. Dočasný výpadek opakuje nejvýše jednou; delší omezení počtu požadavků ponechá na další cyklus a nepokračuje dalšími lokalitami stejného portálu. Pokud selžou i náhradní adresy nebo se změní formát, zachová ostatní výsledky a ukáže chybu či částečné načtení. Datum posledního úplného načtení se při částečném výsledku neposune. Síť práce vrací nejvýše 50 výsledků na dotaz. Úplnost všech nabídek internetu není zaručena. Práce na dálku se zahrne, pokud ji zdroj v načteném seznamu vrátí. Nabídky nezachycené posledních 30 dní se skryjí; dostupnost se ověřuje na původním portálu. AI hodnotí dostupný přehled, který nemusí obsahovat celý inzerát.

Zdroje: [Jobs.cz](https://www.jobs.cz/prace/), [Prace.cz](https://www.prace.cz/nabidky/), [veřejné API Sítě práce](https://sitprace.cz/pro-vyvojare) (CC BY 4.0), [GeoNames](https://www.geonames.org/) (CC BY 4.0, viz `backend/app/data/README.md`).

## Vývoj a ověření

Backend: Python/FastAPI, PostgreSQL. Frontend: React/TypeScript/Vite.

```bash
cd backend
.venv/bin/python -m pytest tests -q
cd ../frontend
npm ci
VITE_API_BASE=/nastenka/api/v1 VITE_BASE_PATH=/nastenka/ npm run build
```

Nové integrační testy běží nad SQLite v paměti a nevyžadují produkční databázi. Historické testy závislé na PostgreSQL se bez testovacího `DATABASE_URL` přeskočí. Starší dokumentace v `docs/` popisuje také odstraněné funkce verze 0.3; aktuální rozsah určuje tento README.

Licence: MIT.

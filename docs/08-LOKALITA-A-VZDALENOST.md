# Lokalita a vzdálenost nabídek

JobRadar umí odhadnout vzdálenost nabídky od vašeho města a podle toho **filtrovat** nebo **řadit** seznam – bez externího geocoding API (statická databáze okresních měst v ČR).

## Nastavení v profilu

1. Otevřete **Profil**.
2. Pole **Domovské město** – zadejte okresní město, např. `Strakonice`, `České Budějovice`, `Tábor`.
3. Volitelně **Výchozí max. vzdálenost (km)** – použije se na stránce Nabídky jako výchozí filtr (1–500 km; prázdné = bez limitu).
4. **Uložit profil**.

Backend při uložení doplní do `preferences.home` souřadnice (`lat`, `lon`). Neznámé město vrátí chybu 400 – použijte běžný název okresního města.

Výchozí šablona profilu pro nové účty má město **Strakonice**; existující účty je potřeba jednou uložit ručně.

## Filtr na stránce Nabídky

Panel **Filtr podle vzdálenosti**:

| Ovládání | Význam |
|----------|--------|
| Max. vzdálenost (km) | Zobrazí jen nabídky do daného radiusu (přepíše výchozí hodnotu z profilu, pokud ji změníte zde). |
| Řazení | Nejnovější / podle skóre / **Nejbližší** (vyžaduje domovské město). |
| Zahrnout remote / hybrid | Nabídky s remote, home office, hybrid v textu lokality – nemají km, ale zůstanou v seznamu. |
| Neznámá lokalita | Nabídky, kde se nepoznalo město v textu (sloupec `?`). |

Sloupec **Vzdálenost**: `42 km`, `remote`, nebo `?`.

## Jak se vzdálenost počítá

- Primárně z pole **Lokalita** u nabídky, záložně z začátku **textu inzerátu**.
- Město se hledá v interní tabulce (~okresní města a větší obce).
- Vzdálenost je **přímá čára** (haversine), ne jízdní čas.
- Remote/hybrid se detekuje podle klíčových slov v lokalitě nebo textu.

## API

`GET /api/v1/jobs` – nové query parametry (vyžadují `preferences.home` v profilu):

| Parametr | Typ | Popis |
|----------|-----|--------|
| `sort` | `imported` \| `score` \| `distance` | Řazení (výchozí `imported`). |
| `max_km` | 1–500 | Filtr radiusu; pokud chybí, použije se `preferences.max_distance_km`. |
| `include_remote` | bool (výchozí `true`) | Remote/hybrid při filtru `max_km`. |
| `include_unknown` | bool (výchozí `true`) | Nabídky bez rozpoznané lokality. |

Odpověď `JobListingOut` obsahuje navíc:

- `distance_km` – číslo nebo `null`
- `location_remote` – boolean
- `location_unknown` – boolean

`PUT /api/v1/profile` – v `preferences` ukládáte `home_city`, `max_distance_km`; server doplní `home`.

`GET /api/v1/geo/places?q=stra` – nápověda pro autocomplete (volitelné).

## Omezení

- Nepozná každou obec – jen města v databázi `app/services/geo.py`.
- Duplicitní nebo chybná lokalita v importu (např. jen kraj) může skončit jako `?`.
- Filtrování probíhá v aplikaci (max. 500 záznamů na dotaz při aktivním filtru/řazení podle vzdálenosti).

## Odložení a zamítnutí nabídky

V **detailu nabídky** (sekce „Rozhodnutí o nabídce“):

- **Odložit** – zvolíte 3/7/14/30 dní a **povinnou poznámku** (proč). Nabídka zmizí z záložky Aktivní do data `snoozed_until`, pak se znovu objeví.
- **Zamítnout** – povinná poznámka; nabídka je v záložce **Zamítnuté**.
- **Vrátit mezi aktivní** – zruší odložení nebo zamítnutí.

API: `POST /jobs/{id}/snooze`, `POST /jobs/{id}/dismiss`, `POST /jobs/{id}/restore-inbox`.  
Seznam: `GET /jobs?inbox=active|snoozed|dismissed` (výchozí `active`).

## Související

- AI hodnocení stále používá textové preference regionů v profilu – filtr vzdálenosti je nezávislý doplněk pro seznam nabídek.
- [07-ETAPA2-PLAN.md](./07-ETAPA2-PLAN.md) – import ze Sítě práce (lokalita v poli `city` / `region`).

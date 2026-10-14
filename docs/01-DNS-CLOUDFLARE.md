# Krok 1: Doména `chcetejelena.cz` → server (Cloudflare)

## IP serveru (origin)

Na VPS:

```bash
curl -4 ifconfig.me
```

Pro `chcetejelena.cz` / produkci: záznam **A** `@` → tato IPv4 (např. `31.31.74.61`), režim **Proxied** (oranžová mrak).

---

## Cloudflare – DNS záznamy

1. [Cloudflare Dashboard](https://dash.cloudflare.com) → zóna **chcetejelena.cz** → **DNS** → **Records**
2. Tabulka:

| Typ | Název | Obsah | Proxy |
|-----|--------|--------|-------|
| **A** | `@` | IPv4 VPS | Proxied |
| **CNAME** | `www` | `chcetejelena.cz` | Proxied |

3. **Nemaž** MX/TXT pro e-mail, pokud doménu používáš pro poštu.

---

## Ověření DNS

```bash
dig +short chcetejelena.cz A
# u Proxied: IP Cloudflare (104.x / 172.x) – normální
```

---

## Cloudflare SSL/TLS

Po nasazení HTTPS na serveru (Apache + Let's Encrypt):

- **SSL/TLS → Overview → Full (strict)**

| Režim | Origin musí |
|--------|-------------|
| **Flexible** | Odpovídat jen na HTTP :80 |
| **Full** | HTTPS na :443 (cert může být self-signed) |
| **Full (strict)** | HTTPS :443 s platným certem (doporučeno) |

---

## Chyba 521 (Web server is down)

Znamená: Cloudflare **nedostane spojení** na origin.

| Příčina | Řešení |
|---------|--------|
| Špatná IP v A záznamu | Opravit na `curl -4 ifconfig.me` |
| Nic neposlouchá na **443** (režim Full/strict) | Certbot + Apache SSL, viz [02-DEPLOY-VPS.md](./02-DEPLOY-VPS.md) |
| Firewall | `ufw allow 80,443/tcp` |
| Apache/nginx neběží | `systemctl status apache2` |

**Není to chyba JobRadaru** – dokud na origin neběží web s TLS/HTTP, Cloudflare ukáže 521.

Po opravě by `https://chcetejelena.cz/` mělo odpovědět (úvodní stránka), ne 521.

---

## Firewall na VPS

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

---

## Kam směřuje aplikace

| URL | Účel |
|-----|------|
| `https://chcetejelena.cz/` | veřejná úvodní stránka |
| `https://chcetejelena.cz/nastenka/` | JobRadar (přihlášení v aplikaci) |

API: `https://chcetejelena.cz/nastenka/api/v1/...`

---

**Další krok:** [02-DEPLOY-VPS.md](./02-DEPLOY-VPS.md)  
**Přihlášení a `.env`:** [03-PRISTUPY-A-KONFIGURACE.md](./03-PRISTUPY-A-KONFIGURACE.md)

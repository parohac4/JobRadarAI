# JobRadar AI

Czech README: [README.md](./README.md)

Job search automation with AI scoring and application tracking. MIT open source.

**Docs index:** [docs/README.md](./docs/README.md) (deployment, Cloudflare, `.env` / login – mostly in Czech).

**Production example:** `https://chcetejelena.cz/nastenka/`

## Local dev

```bash
cp .env.example .env
docker compose up --build
```

Login uses `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env`. On production, after changing `.env`, restart the backend container (see `docs/03-PRISTUPY-A-KONFIGURACE.md`).

## Production (Apache + Docker)

```bash
sudo docker compose --env-file .env -f deploy/docker-compose.apache.yml up -d --build
```

See [docs/02-DEPLOY-VPS.md](./docs/02-DEPLOY-VPS.md).

## License

MIT

# JobRadar AI

Czech README: [README.md](./README.md)

Job search automation with AI scoring, response drafts, and application tracking. Open-source MIT portfolio project.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080) and sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`.

## Stack

FastAPI, PostgreSQL, React + TypeScript, Caddy, optional OpenAI (mock provider by default).

## Demo mode

Set `DEMO_MODE=true` for read-only fictional data suitable for public demos without API keys.

## Tests

```bash
cd backend && pip install -r requirements.txt
pytest tests/test_dedup.py tests/test_email_parse.py -q
```

## License

MIT

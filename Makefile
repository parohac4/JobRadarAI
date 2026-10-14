.PHONY: up down test

up:
	docker compose up --build

down:
	docker compose down

test:
	cd backend && python -m pytest tests/test_dedup.py tests/test_email_parse.py -q

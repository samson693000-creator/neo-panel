.PHONY: up down build logs restart bot-logs backup shell-db ps

up:
	docker compose up -d

build:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart backend frontend

logs:
	docker compose logs -f --tail=100

bot-logs:
	docker compose logs -f backend

ps:
	docker compose ps

backup:
	./scripts/backup.sh

shell-db:
	docker compose exec db psql -U botuser -d botdb

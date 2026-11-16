#!/usr/bin/env bash
# Update only this existing JobRadar stack; do not touch Apache or other services.
set -euo pipefail
umask 077
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
stack_file="$project_dir/deploy/docker-compose.apache.yml"
compose() { docker compose --env-file "$project_dir/.env" -f "$stack_file" "$@"; }

# Refuse a same-name Compose project that belongs to another application.
for service in db backend worker frontend; do
  container_id="$(compose ps --all --quiet "$service")"
  if [[ -z "$container_id" ]]; then
    echo "Chybí existující kontejner $service; automatický upgrade se zastavil." >&2
    exit 1
  fi
  origin_files="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}' "$container_id")"
  case ",$origin_files," in
    *",$stack_file,"*) ;;
    *) echo "Kontejner $service patří jinému Compose souboru; končím." >&2; exit 1 ;;
  esac
done

backup_dir="$project_dir/.backups/aggregator-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
compose exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_dir/database.dump"
for service in backend worker frontend; do
  container_id="$(compose ps --quiet "$service")"
  docker inspect --format '{{.Name}} {{.Image}}' "$container_id" >> "$backup_dir/previous-images.txt"
done

# Build each image before replacing any container. Dependencies and unrelated
# Compose projects remain running. Limit concurrent builds on the shared host.
COMPOSE_PARALLEL_LIMIT=1 compose build backend worker frontend
compose up -d --no-deps backend worker frontend
compose ps backend worker frontend
printf 'Záloha JobRadaru: %s\n' "$backup_dir"
printf 'Kontrola webu: https://chcetejelena.cz/nastenka/\n'

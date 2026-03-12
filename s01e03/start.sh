#!/usr/bin/env bash
set -euo pipefail

APP_ENV="${APP_ENV:-development}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: bash start.sh [options]

Options:
  -h, --help        Show this help message and exit
  --reload          Enable auto-reload (development only)

Environment:
  APP_ENV=development   (default)
  APP_ENV=test
  APP_ENV=production

Examples:
  bash start.sh
  bash start.sh --reload
  APP_ENV=production bash start.sh
EOF
}

RELOAD=""
for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --reload)  RELOAD="--reload" ;;
    *) echo "Error: unknown option: $arg"; echo; usage; exit 1 ;;
  esac
done

ENV_FILE="$PROJECT_ROOT/.env.${APP_ENV}"
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: env file not found: $ENV_FILE"
  exit 1
fi

set -a
# Strip \r (CRLF → LF) to handle env files created on Windows
source <(sed 's/\r//' "$ENV_FILE")
[ -f "$PROJECT_ROOT/.env" ] && source <(sed 's/\r//' "$PROJECT_ROOT/.env")
set +a

HOST="${APP_HOST:-localhost}"
PORT="${APP_PORT:-8000}"

echo "APP_ENV=$APP_ENV"
echo "Running: uvicorn src.main:app --host $HOST --port $PORT $RELOAD"
echo

cd "$PROJECT_ROOT"
exec python -m uvicorn src.main:app --host "$HOST" --port "$PORT" $RELOAD
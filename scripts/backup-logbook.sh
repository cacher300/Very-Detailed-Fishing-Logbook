#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

DATA_FILE="${DATA_FILE:-$APP_DIR/data/logbook.json}"
LOCAL_BACKUP_DIR="${LOCAL_BACKUP_DIR:-$APP_DIR/backups}"
NAS_BACKUP_TARGET="${NAS_BACKUP_TARGET:-}"
KEEP_LOCAL_BACKUPS="${KEEP_LOCAL_BACKUPS:-14}"

timestamp=$(date +"%Y%m%d-%H%M%S")
backup_name="logbook-$timestamp.json"
backup_path="$LOCAL_BACKUP_DIR/$backup_name"

if [ ! -f "$DATA_FILE" ]; then
  echo "No logbook data found at $DATA_FILE" >&2
  exit 1
fi

mkdir -p "$LOCAL_BACKUP_DIR"
cp "$DATA_FILE" "$backup_path"

if command -v python3 >/dev/null 2>&1; then
  python3 -m json.tool "$backup_path" >/dev/null
elif command -v python >/dev/null 2>&1; then
  python -m json.tool "$backup_path" >/dev/null
fi

if [ -n "$NAS_BACKUP_TARGET" ]; then
  case "$NAS_BACKUP_TARGET" in
    *:*)
      remote_host=${NAS_BACKUP_TARGET%%:*}
      remote_dir=${NAS_BACKUP_TARGET#*:}
      ssh "$remote_host" "mkdir -p '$remote_dir'"
      if command -v rsync >/dev/null 2>&1; then
        rsync -a "$backup_path" "$NAS_BACKUP_TARGET/"
      else
        scp "$backup_path" "$NAS_BACKUP_TARGET/"
      fi
      ;;
    *)
      mkdir -p "$NAS_BACKUP_TARGET"
      cp "$backup_path" "$NAS_BACKUP_TARGET/"
      ;;
  esac
else
  echo "NAS_BACKUP_TARGET is not set; kept local backup only at $backup_path" >&2
fi

find "$LOCAL_BACKUP_DIR" -name "logbook-*.json" -type f | sort -r | awk "NR > $KEEP_LOCAL_BACKUPS" | while IFS= read -r old_backup; do
  rm -f "$old_backup"
done

echo "Backup created: $backup_path"

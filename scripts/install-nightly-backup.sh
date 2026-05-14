#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
BACKUP_SCRIPT="$APP_DIR/scripts/backup-logbook.sh"
LOG_FILE="$APP_DIR/backups/backup.log"
TARGET="${1:-${NAS_BACKUP_TARGET:-}}"

if [ -z "$TARGET" ]; then
  cat >&2 <<EOF
Usage:
  $0 user@192.168.3.30:/path/to/fishing-logbook-backups

You can also pass a mounted NAS folder:
  $0 /mnt/nas/fishing-logbook-backups
EOF
  exit 1
fi

mkdir -p "$APP_DIR/backups"
chmod +x "$BACKUP_SCRIPT"

cron_line="0 3 * * * NAS_BACKUP_TARGET='$TARGET' '$BACKUP_SCRIPT' >> '$LOG_FILE' 2>&1"
tmp_cron=$(mktemp)

crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" > "$tmp_cron" || true
printf "%s\n" "$cron_line" >> "$tmp_cron"
crontab "$tmp_cron"
rm -f "$tmp_cron"

echo "Installed nightly Fishing Logbook backup for 3:00 AM."
echo "Target: $TARGET"
echo "Log: $LOG_FILE"

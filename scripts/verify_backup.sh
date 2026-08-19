#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: BACKUP_FILE=/secure/path/backup.dump scripts/verify_backup.sh [--dry-run]

Verify that a PostgreSQL custom-format backup exists, is readable, and can be
listed by pg_restore. This script never creates, restores, or modifies a backup
or database, and it never prints the configured backup path.

Options:
  --dry-run  Describe the checks without reading a backup file.
  --help     Show this help text.
EOF
}

dry_run=false
case "${1:-}" in
  "") ;;
  --dry-run) dry_run=true ;;
  --help|-h) usage; exit 0 ;;
  *) echo "Backup verification failed: unsupported option." >&2; usage >&2; exit 2 ;;
esac

if [[ "$dry_run" == "true" ]]; then
  echo "DRY RUN: would verify BACKUP_FILE and inspect it with pg_restore --list."
  echo "No backup or database changes would occur."
  exit 0
fi

if [[ -z "${BACKUP_FILE:-}" ]]; then
  echo "Backup verification failed: BACKUP_FILE is not configured." >&2
  exit 1
fi

if [[ ! -f "$BACKUP_FILE" || ! -r "$BACKUP_FILE" ]]; then
  echo "Backup verification failed: backup file is missing or unreadable." >&2
  exit 1
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "Backup verification failed: pg_restore is unavailable." >&2
  exit 1
fi

if ! pg_restore --list "$BACKUP_FILE" >/dev/null 2>&1; then
  echo "Backup verification failed: archive cannot be listed by pg_restore." >&2
  exit 1
fi

echo "Backup file: readable"
echo "PostgreSQL archive listing: OK"
echo "No backup or database changes were made."

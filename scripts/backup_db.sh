#!/usr/bin/env bash
# Sauvegarde quotidienne de la base MySQL TechConnect Bénin.
# Usage : bash scripts/backup_db.sh
# Rotation : conserve les 14 derniers fichiers.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

read -r DB_NAME ROOT_PASSWORD <<< "$(
    python3 -c "from dotenv import dotenv_values; v = dotenv_values('.env'); print(v['DB_NAME'], v['DB_ROOT_PASSWORD'])"
)"

BACKUP_DIR="$REPO_DIR/backups"
mkdir -p "$BACKUP_DIR"

HORODATAGE="$(date +%Y-%m-%d_%H%M)"
FICHIER="$BACKUP_DIR/${DB_NAME}_${HORODATAGE}.sql.gz"

docker exec -e MYSQL_PWD="$ROOT_PASSWORD" techconnect_db \
    mysqldump --single-transaction --routines --triggers -uroot "$DB_NAME" \
    | gzip > "$FICHIER"

find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +14 -delete

echo "Sauvegarde réussie : $FICHIER"
echo "Sauvegardes conservées : $(find "$BACKUP_DIR" -type f -name '*.sql.gz' | wc -l)"
#!/bin/bash
# HPCFlow - Cleanup Script

# Set variables
APP_DIR="$(dirname "$0")"
BACKEND_DIR="$APP_DIR/../backend"
FRONTEND_DIR="$APP_DIR/../frontend"
DATA_DIR="$APP_DIR/../data"
LOG_DIR="$APP_DIR/../logs"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Exit on error
set -e

log "🗑️ Starting HPCFlow Cleanup"

# Remove logs
if [ -d "$LOG_DIR" ]; then
    log "🗑️ Removing logs directory: $LOG_DIR"
    rm -rf "$LOG_DIR"
fi

# Remove backups
for file in "$BACKEND_DIR"/*.py.bak "$FRONTEND_DIR"/*.html.bak; do
    if [ -f "$file" ]; then
        log "🗑️ Removing backup: $file"
        rm "$file"
    fi
done

# Remove old Docker images
log "🗑️ Removing old Docker images"
docker rmi -f $(docker images -q) 2>/dev/null || true

# Remove containers
log "🗑️ Removing containers"
docker rm -f $(docker ps -aq) 2>/dev/null || true

log "✅ HPCFlow Cleanup Complete"
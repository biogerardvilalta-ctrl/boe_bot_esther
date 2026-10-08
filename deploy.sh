#!/bin/bash
# Script de deploy automàtic al servidor Hetzner
# Executa aquest script al servidor per actualitzar l'aplicació:
#   chmod +x deploy.sh
#   ./deploy.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()     { echo -e "${BLUE}[DEPLOY]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${APP_DIR}"

log "Baixant canvis del repositori git..."
git pull origin main || error "Error fent git pull"

log "Reconstruint imatges Docker..."
docker compose build --parallel || error "Error construint les imatges"

log "Reiniciant contenidors..."
docker compose up -d --remove-orphans || error "Error iniciant contenidors"

success "Deploy completat! El bot està en marxa."
docker compose ps

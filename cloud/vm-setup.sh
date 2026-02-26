#!/usr/bin/env bash
# =============================================================================
# cloud/vm-setup.sh – One-time setup for the Oracle Cloud free-tier VM
#
# Run this ONCE after creating the OCI instance (as the default opc/ubuntu user):
#   bash vm-setup.sh
#
# What it does:
#   1. Installs Docker + Docker Compose
#   2. Opens port 8080 in the VM's local iptables (OCI VCN Security List must
#      also allow TCP 8080 – do this in the OCI Console)
#   3. Creates /opt/valuecell/{data,.env} with safe permissions
#   4. Logs in to GitHub Container Registry (GHCR) so Docker can pull the image
#   5. Pulls the image and starts the app via docker compose
#
# Before running:
#   export GHCR_TOKEN=<your GitHub PAT with read:packages scope>
#   export GHCR_OWNER=<your GitHub username, e.g. lukecold>
# =============================================================================
set -euo pipefail

GHCR_OWNER="${GHCR_OWNER:?Set GHCR_OWNER=<your-github-username>}"
GHCR_TOKEN="${GHCR_TOKEN:?Set GHCR_TOKEN=<github-PAT-with-read:packages>}"
DEPLOY_DIR="/opt/valuecell"

info()  { echo "  [INFO]  $*"; }
ok()    { echo "  [ OK ]  $*"; }

# ── 1. System update + Docker ─────────────────────────────────────────────────
info "Updating system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
  ca-certificates curl gnupg lsb-release iptables-persistent

info "Installing Docker..."
# Official Docker install (works on Ubuntu 22.04 / 24.04 and OL8/OL9)
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
fi

sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
ok "Docker $(docker --version) ready"

# Docker Compose v2 (plugin bundled with modern Docker, ensure it's available)
docker compose version &>/dev/null || sudo apt-get install -y docker-compose-plugin
ok "Docker Compose $(docker compose version --short) ready"

# ── 2. Open port 8080 in iptables ─────────────────────────────────────────────
# OCI instances use iptables by default; the VCN Security List is a separate layer.
info "Opening port 8080 in iptables..."
if ! sudo iptables -C INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null; then
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
fi
# Persist rules across reboots
sudo netfilter-persistent save
ok "Port 8080 open"

# ── 3. App directory + env file ───────────────────────────────────────────────
info "Creating $DEPLOY_DIR..."
sudo mkdir -p "${DEPLOY_DIR}/data"
sudo chown -R "$USER:$USER" "$DEPLOY_DIR"
chmod 700 "$DEPLOY_DIR"

# Create a .env stub if it doesn't already exist
if [[ ! -f "${DEPLOY_DIR}/.env" ]]; then
  cat > "${DEPLOY_DIR}/.env" <<'ENVEOF'
# /opt/valuecell/.env – loaded automatically by docker compose
# Add your AI provider keys here. This file is NOT committed to git.

OPENAI_API_KEY=
OPENROUTER_API_KEY=
GOOGLE_API_KEY=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
ANTHROPIC_API_KEY=
ENVEOF
  chmod 600 "${DEPLOY_DIR}/.env"
  ok "Created ${DEPLOY_DIR}/.env  ← fill in your API keys"
else
  ok "${DEPLOY_DIR}/.env already exists, skipping"
fi

# Copy docker-compose.yml into the deploy dir
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "${SCRIPT_DIR}/docker-compose.yml" "${DEPLOY_DIR}/docker-compose.yml"
ok "Copied docker-compose.yml to $DEPLOY_DIR"

# ── 4. Log in to GHCR and pull the image ─────────────────────────────────────
info "Logging in to ghcr.io..."
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_OWNER" --password-stdin
ok "Logged in to ghcr.io"

info "Pulling image ghcr.io/${GHCR_OWNER}/valuecell:latest ..."
GHCR_OWNER="$GHCR_OWNER" docker compose -f "${DEPLOY_DIR}/docker-compose.yml" pull
ok "Image pulled"

# ── 5. Start the app ──────────────────────────────────────────────────────────
info "Starting valuecell..."
GHCR_OWNER="$GHCR_OWNER" \
  docker compose -f "${DEPLOY_DIR}/docker-compose.yml" \
    --env-file "${DEPLOY_DIR}/.env" \
    up -d
ok "valuecell is up"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Setup complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
PUBLIC_IP=$(curl -s --max-time 5 http://169.254.169.254/opc/v1/instance/networkInterfaces/ \
  2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['publicIp'])" \
  2>/dev/null || echo "<your-vm-public-ip>")
echo "  App URL  : http://${PUBLIC_IP}:8080"
echo "  Static IP: ${PUBLIC_IP}  ← whitelist this in Binance"
echo ""
echo "  To view logs : docker logs -f valuecell"
echo "  To restart   : docker compose -f /opt/valuecell/docker-compose.yml restart"
echo "  To update    : docker compose -f /opt/valuecell/docker-compose.yml pull && \\"
echo "                 docker compose -f /opt/valuecell/docker-compose.yml up -d"
echo ""
echo "  IMPORTANT: In the OCI Console → Networking → VCN → Security Lists,"
echo "  add an Ingress Rule for TCP port 8080 from 0.0.0.0/0"
echo ""
echo "  Don't forget to fill in your API keys:"
echo "    nano /opt/valuecell/.env"
echo "    docker compose -f /opt/valuecell/docker-compose.yml up -d"
echo ""

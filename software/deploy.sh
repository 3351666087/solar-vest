#!/bin/bash
# Deploy the SolarVest console to a Docker host that already runs a Caddy edge container
# on a shared Docker network.
#
# Usage:
#   SV_SSH_HOST=myserver SV_DOMAIN=console.example.org ./deploy.sh
#
# Environment variables (all optional; neutral defaults shown):
#   SV_SSH_HOST        SSH host alias or user@host of the server           (default: solarvest-host)
#   SV_REMOTE_DIR      directory on the server for the app files + env file  (default: /opt/solarvest)
#   SV_DOCKER_NETWORK  Docker network shared with the Caddy edge container   (default: web)
#   SV_CADDYFILE       path of the Caddyfile on the server host              (default: /opt/caddy/Caddyfile)
#   SV_EDGE_CONTAINER  name of the running Caddy container                   (default: caddy)
#   SV_DOMAIN          public site domain for the console                    (default: console.example.org)
#   SV_SERVER_ENV      local env file copied to the server (chmod 600)       (default: ~/.config/solarvest/server.env)
set -euo pipefail
SV_SSH_HOST="${SV_SSH_HOST:-solarvest-host}"
SV_REMOTE_DIR="${SV_REMOTE_DIR:-/opt/solarvest}"
SV_DOCKER_NETWORK="${SV_DOCKER_NETWORK:-web}"
SV_CADDYFILE="${SV_CADDYFILE:-/opt/caddy/Caddyfile}"
SV_EDGE_CONTAINER="${SV_EDGE_CONTAINER:-caddy}"
SV_DOMAIN="${SV_DOMAIN:-console.example.org}"
SV_SERVER_ENV="${SV_SERVER_ENV:-$HOME/.config/solarvest/server.env}"
HERE="$(cd "$(dirname "$0")" && pwd)"

tar -C "$HERE/server" --exclude __pycache__ -czf - server.py console.html Dockerfile \
  | ssh "$SV_SSH_HOST" "sudo mkdir -p '$SV_REMOTE_DIR' && sudo tar -xzf - -C '$SV_REMOTE_DIR'"
ssh "$SV_SSH_HOST" "sudo tee '$SV_REMOTE_DIR/server.env' >/dev/null && sudo chmod 600 '$SV_REMOTE_DIR/server.env'" < "$SV_SERVER_ENV"

# The remote script reads its settings from positional arguments (no local expansion inside it).
ssh "$SV_SSH_HOST" bash -s -- "$SV_REMOTE_DIR" "$SV_DOCKER_NETWORK" "$SV_CADDYFILE" "$SV_EDGE_CONTAINER" "$SV_DOMAIN" <<'REMOTE'
set -euo pipefail
REMOTE_DIR="$1"; NETWORK="$2"; CADDYFILE="$3"; EDGE="$4"; DOMAIN="$5"
cd "$REMOTE_DIR"
sudo docker build -q -t solarvest:latest . >/dev/null
sudo docker rm -f solarvest >/dev/null 2>&1 || true
sudo docker run -d --name solarvest --restart unless-stopped \
  --network "$NETWORK" --env-file "$REMOTE_DIR/server.env" \
  -v solarvest_data:/data --memory 192m solarvest:latest >/dev/null

if ! grep -q "$DOMAIN" "$CADDYFILE"; then
  sudo cp "$CADDYFILE" "$CADDYFILE.bak-$(date +%Y%m%d-%H%M%S)"
  sudo tee -a "$CADDYFILE" >/dev/null <<CADDY

# SolarVest PMB-H remote console
$DOMAIN {
	encode zstd gzip
	reverse_proxy solarvest:8790 {
		flush_interval -1
	}
}
CADDY
fi
sudo docker exec "$EDGE" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null
sudo docker exec "$EDGE" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
sleep 3
sudo docker ps --filter name=solarvest --format '{{.Names}} {{.Status}}'
REMOTE
echo DEPLOY_DONE

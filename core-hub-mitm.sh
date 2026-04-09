#!/bin/bash
# Start Core Hub with MITM as reverse proxy

set -e

cd /home/ubuntu/molo17/DB2-MSS_53e4/gluesync-docker

# Clean up old containers
podman rm -f gluesync-core-hub-backend 2>/dev/null || true
podman rm -f gluesync_gluesync-core-hub_1 2>/dev/null || true
podman rm -f gluesync-core-hub-ssl 2>/dev/null || true

echo "=== Starting Core Hub on port 1719 (backend) ==="
podman run -d --name gluesync-core-hub-backend \
  --network gluesync-net \
  -p 1719:1717 \
  -e SSL_ENABLED=true \
  -e LOG_CONFIG_FILE=/opt/gluesync/shared/logback.xml \
  -e ADMIN_PASS='${ADMIN_PASS}' \
  -v $(pwd)/shared:/opt/gluesync/shared:Z \
  -v $(pwd)/bootstrap-core-hub.json:/opt/gluesync/data/bootstrap-core-hub.json:Z \
  -v $(pwd)/data/core-hub:/opt/gluesync/data:Z \
  -v $(pwd)/logs/core-hub:/opt/gluesync/logs:Z \
  docker.io/molo17/gluesync-core-hub:2.2.4.3

echo "Waiting for Core Hub to start..."
sleep 10

if podman ps | grep -q gluesync-core-hub-backend; then
    echo "✓ Core Hub running on port 1719"
else
    echo "✗ Core Hub failed to start"
    podman logs gluesync-core-hub-backend
    exit 1
fi

echo ""
echo "=== Starting MITM as reverse proxy on port 1717 ==="
echo "This will capture all API calls to Core Hub"
echo ""

cd /home/ubuntu/_qoder
~/.local/bin/mitmdump \
  -s capture_api.py \
  --mode reverse:https://localhost:1719 \
  --listen-port 1717 \
  --ssl-insecure \
  --set block_global=false

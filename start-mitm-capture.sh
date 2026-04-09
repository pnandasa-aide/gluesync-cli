#!/bin/bash
# Start MITM proxy for API capture
# MITM listens on port 1716 and forwards to Core Hub on port 1717

cd /home/ubuntu/_qoder

echo "=== Starting MITM Proxy for API Capture ==="
echo ""
echo "This will:"
echo "  - Listen on port 1716 (MITM)"
echo "  - Forward to Core Hub on port 1717"
echo "  - Capture all API calls to captured_api_calls.json"
echo ""
echo "Prerequisites:"
echo "  1. Core Hub must be running on port 1717 (via podman-compose)"
echo "  2. Traefik should be running on 8080/8443"
echo ""
echo "Access GlueSync via:"
echo "  - https://localhost:1716/ui/index.html (captured via MITM)"
echo "  - https://localhost:1717/ui/index.html (direct, NOT captured)"
echo "  - https://localhost:8443 (via Traefik, NOT captured)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Check if Core Hub is running on 1717
if ! ss -tlnp | grep -q ':1717 '; then
    echo "⚠️  Core Hub is not running on port 1717!"
    echo "Start it first:"
    echo "  cd /home/ubuntu/molo17/DB2-MSS_53e4/gluesync-docker"
    echo "  podman-compose up -d gluesync-core-hub"
    exit 1
fi

# Check if port 1716 is available
if ss -tlnp | grep -q ':1716 '; then
    echo "⚠️  Port 1716 is already in use!"
    exit 1
fi

# Clear previous capture
echo "[]" > captured_api_calls.json

# Start MITM on port 1716, forwarding to 1717
~/.local/bin/mitmdump \
  -s capture_api.py \
  --mode reverse:https://localhost:1717 \
  --listen-port 1716 \
  --ssl-insecure \
  --set block_global=false

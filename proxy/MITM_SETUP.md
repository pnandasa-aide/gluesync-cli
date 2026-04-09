# MITM Proxy Setup for API Capture

This document describes how to set up and use mitmproxy to capture GlueSync API calls for reverse engineering and automation.

## Overview

We use **mitmproxy** as a reverse proxy to intercept HTTPS traffic between the GlueSync Web UI and the Core Hub API. This allows us to capture the complete API flow including authentication, agent provisioning, and entity management.

## Architecture

```
Browser/Web UI ──HTTPS──> MITM Proxy (port 1717) ──HTTPS──> Core Hub (port 1719)
                              │
                              └──> Captures all API calls
```

## Prerequisites

- Python 3 installed
- Root access to the GlueSync host (or ability to run containers)
- GlueSync Core Hub running with SSL enabled

## Installation

### 1. Install mitmproxy

```bash
pip3 install mitmproxy
```

Verify installation:
```bash
~/.local/bin/mitmproxy --version
```

### 2. Create Capture Script

Create `/home/ubuntu/_qoder/capture_api.py`:

```python
#!/usr/bin/env python3
"""
MITM Proxy addon to capture GlueSync API calls
"""

import json
import os
from datetime import datetime
from mitmproxy import http

LOG_FILE = "/home/ubuntu/_qoder/captured_api_calls.json"

def load_existing_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_logs(logs):
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

class APICapture:
    def __init__(self):
        self.logs = load_existing_logs()
        print(f"Loaded {len(self.logs)} existing log entries")
    
    def request(self, flow: http.HTTPFlow) -> None:
        # Only capture API calls (not static assets)
        if not any(flow.request.path.startswith(p) for p in ['/pipelines', '/authentication', '/agents', '/api/']):
            return
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "method": flow.request.method,
            "url": flow.request.url,
            "path": flow.request.path,
            "headers": dict(flow.request.headers),
        }
        
        if flow.request.content:
            try:
                body = flow.request.content.decode('utf-8')
                entry["request_body"] = json.loads(body) if body else None
            except:
                entry["request_body_raw"] = flow.request.content.hex()[:200]
        
        flow.metadata["capture_entry"] = entry
    
    def response(self, flow: http.HTTPFlow) -> None:
        if "capture_entry" not in flow.metadata:
            return
        
        entry = flow.metadata["capture_entry"]
        entry["status_code"] = flow.response.status_code
        entry["response_headers"] = dict(flow.response.headers)
        
        if flow.response.content:
            try:
                body = flow.response.content.decode('utf-8')
                entry["response_body"] = json.loads(body) if body else None
            except:
                entry["response_body_raw"] = flow.response.content.hex()[:200]
        
        self.logs.append(entry)
        save_logs(self.logs)
        
        print(f"\n[{entry['method']}] {entry['path']} -> {entry['status_code']}")

addons = [APICapture()]
```

## Setup Steps

### Step 1: Prepare Core Hub

Stop any existing Core Hub on port 1717 and start it on a different port (1719):

```bash
# Stop existing container
export PATH=$HOME/.local/bin:$PATH
podman stop gluesync-core-hub-ssl 2>/dev/null

# Start Core Hub on port 1719
cd /home/ubuntu/molo17/DB2-MSS_53e4/gluesync-docker

podman run -d --name gluesync-core-hub-backend \
  --network gluesync-net \
  -p 1719:1717 \
  -e SSL_ENABLED=true \
  -e LOG_CONFIG_FILE=/opt/gluesync/shared/logback.xml \
  -e ADMIN_PASS='<ADMIN_PASSWORD>' \
  -v ./shared:/opt/gluesync/shared:Z \
  -v ./data/core-hub:/opt/gluesync/data:Z \
  -v ./bootstrap-core-hub.json:/opt/gluesync/data/bootstrap-core-hub.json:Z \
  -v ./logs/core-hub:/opt/gluesync/logs:Z \
  docker.io/molo17/gluesync-core-hub:2.2.4.3
```

Wait for Core Hub to start:
```bash
sleep 10
podman ps | grep core-hub
```

### Step 2: Start MITM Proxy

Start mitmproxy in reverse proxy mode on port 1717, forwarding to Core Hub on 1719:

```bash
cd /home/ubuntu/_qoder

~/.local/bin/mitmdump \
  -s capture_api.py \
  --mode reverse:https://localhost:1719 \
  --listen-port 1717 \
  --ssl-insecure \
  --set block_global=false
```

Parameters explained:
- `-s capture_api.py` - Load our capture addon
- `--mode reverse:https://localhost:1719` - Reverse proxy mode to Core Hub
- `--listen-port 1717` - Listen on port 1717 (standard Core Hub port)
- `--ssl-insecure` - Don't verify SSL certificates
- `--set block_global=false` - Allow connections from any IP

### Step 3: Access Web UI Through Proxy

Open your browser and navigate to:

```
https://localhost:1717/ui/index.html
```

Or if accessing from another machine:
```
https://<server-ip>:1717/ui/index.html
```

**Note**: You'll see a certificate warning because mitmproxy uses its own certificate. Accept the risk and continue, or install the mitmproxy CA certificate.

### Step 4: Capture API Calls

1. Log in to the Web UI
2. Perform actions (create pipeline, add agents, configure entities)
3. All API calls are automatically captured to `captured_api_calls.json`

## Viewing Captured Data

### Real-time Output

The proxy prints captured calls to the console:
```
[POST] /authentication/login -> 200
[GET] /pipelines -> 200
[PUT] /pipelines/b2f6e46a/agents/00c7ac81/config/credentials -> 202
```

### Analyzing Capture File

View the full capture:
```bash
cat /home/ubuntu/_qoder/captured_api_calls.json | python3 -m json.tool | less
```

List all captured endpoints:
```bash
cat /home/ubuntu/_qoder/captured_api_calls.json | python3 -c "
import json,sys
data=json.load(sys.stdin)
for d in data:
    print(f\"{d['method']:6} {d['path']}\")
"
```

## Troubleshooting

### Issue: "Client TLS handshake failed"
**Cause**: Browser doesn't trust mitmproxy's certificate
**Solution**: Accept the certificate warning in browser or install the mitmproxy CA

### Issue: "Connection refused"
**Cause**: Core Hub not running on backend port
**Solution**: Verify Core Hub is running on port 1719

### Issue: "block_global" errors
**Cause**: mitmproxy blocking non-local connections
**Solution**: Use `--set block_global=false` flag

### Issue: Port 1717 already in use
**Cause**: Another service using port 1717
**Solution**: Stop the service or use a different port

## Security Considerations

⚠️ **WARNING**: The capture file contains sensitive data including:
- Authentication tokens
- Database credentials
- API keys

**Best Practices**:
1. Delete capture files when no longer needed
2. Don't commit capture files to version control
3. Use placeholder credentials in documentation
4. Restrict access to capture files

## Stopping the Proxy

To stop the MITM proxy:
```bash
pkill -f mitmdump
```

To restore normal Core Hub operation:
```bash
# Stop proxy
pkill -f mitmdump

# Stop backend container
podman stop gluesync-core-hub-backend

# Start Core Hub normally on port 1717
# (use your original podman run command)
```

## Example Workflow

```bash
# 1. Start backend Core Hub on port 1719
podman run -d --name gluesync-core-hub-backend ...

# 2. Start MITM proxy on port 1717
cd /home/ubuntu/_qoder
~/.local/bin/mitmdump -s capture_api.py --mode reverse:https://localhost:1719 --listen-port 1717 --ssl-insecure --set block_global=false

# 3. Open browser to https://localhost:1717/ui/index.html
# 4. Perform actions in UI
# 5. Check captured_api_calls.json for API details

# 6. Clean up when done
pkill -f mitmdump
podman stop gluesync-core-hub-backend
```

## Files Generated

| File | Description |
|------|-------------|
| `captured_api_calls.json` | All captured API calls with request/response bodies |
| `~/.mitmproxy/mitmproxy-ca-cert.pem` | CA certificate for trusting the proxy |

## Next Steps

After capturing API calls:
1. Analyze the flow in `captured_api_calls.json`
2. Document the API endpoints and payloads
3. Create automation scripts based on captured patterns
4. Delete or secure the capture file when done

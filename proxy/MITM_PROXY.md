# MITM Proxy for GlueSync API Capture

This document explains how to use the MITM (Man-in-the-Middle) proxy to capture and analyze GlueSync API calls.

## Table of Contents

- [Why Use MITM Proxy?](#why-use-mitm-proxy)
- [Architecture](#architecture)
- [Port Configuration](#port-configuration)
- [Setup and Usage](#setup-and-usage)
- [Log Analysis](#log-analysis)
- [Troubleshooting](#troubleshooting)

---

## Why Use MITM Proxy?

The MITM proxy serves as a **runtime reverse proxy** for API observability and reverse engineering:

1. **API Discovery** - Capture undocumented endpoints when using the GlueSync UI
2. **Reverse Engineering** - Understand request/response formats for automation
3. **Debugging** - Inspect API calls to diagnose issues
4. **Documentation** - Record API behavior for CLI development
5. **Security Analysis** - Verify what data is being transmitted

### Use Cases

| Scenario | MITM Port | Direct Port |
|----------|-----------|-------------|
| UI Development / API Discovery | 1716 | - |
| Normal Operations | - | 1717 |
| Debugging API Issues | 1716 | 1717 (compare) |
| CLI Development | 1716 | 1717 (verify) |

---

## Architecture

### Port Separation Principle

We use **strict port separation** to avoid conflicts:

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT (Browser/CLI)                    │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
        ┌──────────────┐              ┌──────────────┐
        │  MITM Proxy  │              │   Core Hub   │
        │   Port 1716  │─────────────▶│   Port 1717  │
        │  (Capture)   │   Forward    │   (Direct)   │
        └──────────────┘              └──────────────┘
               │                              │
               ▼                              ▼
        ┌──────────────┐              ┌──────────────┐
        │ Capture Log  │              │  GlueSync    │
        │  (JSON File) │              │   Services   │
        └──────────────┘              └──────────────┘
```

### Traffic Flow

1. **Standard Port (1717)**: Direct access to Core Hub - use for normal operations
2. **MITM Port (1716)**: Traffic flows through mitmdump proxy, gets logged, then forwarded to 1717

---

## Port Configuration

| Port | Service | Purpose | When to Use |
|------|---------|---------|-------------|
| **1716** | MITM Proxy | API capture and logging | When you need to record/analyze API calls |
| **1717** | Core Hub | Direct access to GlueSync | For normal operations, better performance |
| **8080** | Traefik | HTTP reverse proxy | Alternative access path |
| **8443** | Traefik | HTTPS reverse proxy | Secure alternative access |

### Key Point

- **Port 1716** = Capturing mode (slower, logs everything)
- **Port 1717** = Direct mode (faster, no logging)

---

## Setup and Usage

### Prerequisites

```bash
# Install mitmproxy
pip3 install mitmproxy

# Or via package manager
sudo apt-get install mitmproxy
```

### Starting MITM Capture

```bash
# 1. Ensure Core Hub is running on port 1717
podman-compose up -d gluesync-core-hub

# 2. Start MITM capture
./start-mitm-capture.sh

# 3. Access via MITM port (1716) for capture
https://localhost:1716/ui/index.html

# 4. Perform actions in UI (login, create pipeline, etc.)

# 5. Stop MITM (Ctrl+C) when done - logs are saved automatically
```

### The Capture Script

```bash
#!/bin/bash
# start-mitm-capture.sh

OUTPUT_FILE="captured_api_calls_$(date +%Y%m%d_%H%M%S).json"

echo "Starting MITM proxy on port 1716..."
echo "Forwarding to Core Hub on port 1717"
echo "Logs will be saved to: $OUTPUT_FILE"
echo ""
echo "Access UI at: https://localhost:1716/ui/index.html"
echo ""

mitmdump \
  --mode reverse:https://localhost:1717 \
  --listen-port 1716 \
  --ssl-insecure \
  -s capture_api.py
```

### Capture Configuration

The `capture_api.py` addon script filters and formats API calls:

```python
# capture_api.py - Key logic
from mitmproxy import http
import json

def request(flow: http.HTTPFlow) -> None:
    # Only capture GlueSync API calls
    if flow.request.pretty_url.startswith("https://localhost:1717"):
        capture_data = {
            "timestamp": time.time(),
            "method": flow.request.method,
            "path": flow.request.path,
            "headers": dict(flow.request.headers),
            "body": safe_parse_body(flow.request.content)
        }
        # Save to file...
```

---

## Log Analysis

### Capture Output Files

| File | Description |
|------|-------------|
| `captured_api_calls_*.json` | All captured API calls with request/response |
| `capture_api.py` | MITM addon script for filtering |

### Reading the Log

```bash
# View all captured endpoints
cat captured_api_calls.json | python3 -c "
import json,sys
data=json.load(sys.stdin)
for d in data:
    print(f\"{d['timestamp']} {d['method']:6} {d['path']}\")
"
```

### Sample API Call Structure

```json
{
  "timestamp": 1712345678.123,
  "method": "PUT",
  "path": "/pipelines/8aeb9fb6/config/entities",
  "request_headers": {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIs...",
    "Content-Type": "application/json"
  },
  "request_body": {
    "entities": [{
      "entityId": "98fd97b8",
      "entityName": "GSLIBTST.CUSTOMERS",
      "agentEntities": [...]
    }]
  },
  "response_status": 200,
  "response_body": {...}
}
```

### Identifying Key API Calls

#### 1. Authentication
```bash
# Look for login requests
grep -A5 '"method": "POST"' captured_api_calls.json | grep -A3 'authentication/login'
```

**Key fields:**
- `request_body.username` / `request_body.password`
- `response_body.apiToken` (JWT token)

#### 2. Pipeline Creation
```bash
# Find pipeline creation
grep -B2 -A10 '"path": "/pipelines"' captured_api_calls.json | grep -A10 '"method": "POST"'
```

**Key fields:**
- `request_body.name` - Pipeline name
- `request_body.description` - Pipeline description
- `response_body.pipelineId` - Created pipeline ID

#### 3. Entity Configuration
```bash
# Find entity updates
grep -B2 -A20 'config/entities' captured_api_calls.json
```

**Key fields:**
- `request_body.entities[].entityId` - Entity identifier
- `request_body.entities[].entityName` - Table name
- `request_body.entities[].agentEntities[]` - Source/target configuration
- `agentEntities[].entityType.snapshotWriteMethod` - MERGE/UPSERT/INSERT

#### 4. Runtime Operations
```bash
# Find CDC start/stop commands
grep -B2 -A5 'commands/sync' captured_api_calls.json
```

**Key patterns:**
- `POST /pipelines/{id}/commands/sync/redo` - Start with reset
- `POST /pipelines/{id}/commands/sync/stop` - Stop entity
- Query params: `entity`, `withSnapshot`, `snapshotWriteMethod`

### Filtering Examples

```bash
# Get all unique endpoints
cat captured_api_calls.json | python3 -c "
import json,sys
data=json.load(sys.stdin)
endpoints=set(f\"{d['method']} {d['path']}\" for d in data)
for e in sorted(endpoints): print(e)
"

# Find requests with specific body content
cat captured_api_calls.json | python3 -c "
import json,sys
data=json.load(sys.stdin)
for d in data:
    body = d.get('request_body', {})
    if 'entityName' in str(body):
        print(f\"{d['method']} {d['path']} -> {body.get('entityName', 'N/A')}\")
"

# Extract authentication tokens
cat captured_api_calls.json | python3 -c "
import json,sys
data=json.load(sys.stdin)
for d in data:
    if 'login' in d['path'] and d['response_body']:
        token = d['response_body'].get('apiToken', '')
        print(f\"Token: {token[:50]}...\")
"
```

---

## Troubleshooting

### MITM Not Capturing

**Problem:** No logs being written

**Solutions:**
1. Verify Core Hub is running on port 1717
2. Check you're accessing port 1716, not 1717
3. Ensure `capture_api.py` is in the same directory

### SSL Certificate Errors

**Problem:** Browser shows certificate warning

**Solution:** This is expected for MITM. Either:
- Accept the certificate in browser
- Or install mitmproxy CA certificate

### Port Already in Use

**Problem:** `Address already in use` error

**Solution:**
```bash
# Find and kill process using port 1716
sudo lsof -ti:1716 | xargs kill -9
```

### Empty Capture File

**Problem:** `captured_api_calls.json` is empty

**Solutions:**
1. Ensure traffic is going through port 1716
2. Check that `capture_api.py` has no syntax errors
3. Verify the API calls are to `/api/*` or `/pipelines/*` paths

---

## Best Practices

1. **Use 1717 for normal work** - Only use 1716 when you need to capture
2. **Rotate log files** - Capture files can grow large; use timestamps
3. **Sanitize before sharing** - Remove tokens and passwords from logs
4. **Capture incrementally** - Do one action at a time for clearer logs

---

## Related Files

| File | Purpose |
|------|---------|
| `start-mitm-capture.sh` | Start MITM proxy with logging |
| `capture_api.py` | MITM addon for filtering/formatting |
| `captured_api_calls_*.json` | Generated log files |

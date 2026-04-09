# GlueSync Automator Setup Documentation

> ⚠️ **SECURITY NOTICE**: This document contains placeholder credentials marked with `< >`.
> Replace all placeholders with actual values before use:
> - `<ADMIN_PASSWORD>` - Core Hub admin password

## Overview
This document describes the setup and configuration of GlueSync Automator with Podman, including all custom adjustments made to the GlueSync compose environment.

## System Environment
- **OS**: Ubuntu 22.04
- **Container Runtime**: Podman (rootless)
- **Network**: gluesync-net (CNI bridge)
- **Host IP**: 192.168.13.53

## Download and Installation

### 1. Download Automator Binary
```bash
# Download from MOLO17 official source
wget "https://molo17.com/gs-content/gluesync-automator/gluesync-automator-linux" \
  -O ~/gluesync-automator/gluesync-automator

# Make executable
chmod +x ~/gluesync-automator/gluesync-automator
```

### 2. Create Directory Structure
```bash
mkdir -p ~/gluesync-automator
```

## Core Hub Configuration Changes

### SSL Enablement (Required for Automator)

The Automator is hardcoded to use `https://localhost:1717`. The Core Hub must run with SSL enabled.

#### Original Configuration (HTTP)
- **URL**: http://192.168.13.53:1717
- **SSL_ENABLED**: false

#### New Configuration (HTTPS)
- **URL**: https://192.168.13.53:1717
- **SSL_ENABLED**: true

#### Podman Run Command for Core Hub with SSL
```bash
podman run -d --name gluesync-core-hub-ssl \
  --network gluesync-net \
  -p 1717:1717 \
  -e SSL_ENABLED=true \
  -e LOG_CONFIG_FILE=/opt/gluesync/shared/logback.xml \
  -e ADMIN_PASS='<ADMIN_PASSWORD>' \
  -v ./shared:/opt/gluesync/shared:Z \
  -v ./data:/opt/gluesync/data:Z \
  -v ./logs:/opt/gluesync/logs:Z \
  docker.io/molo17/gluesync-core-hub:2.2.4.3
```

### Required Volumes
| Volume | Purpose |
|--------|---------|
| `./shared` | Shared configuration (logback.xml) |
| `./data` | Core Hub data directory |
| `./logs` | Log files |

### Environment Variables
| Variable | Value | Description |
|----------|-------|-------------|
| `SSL_ENABLED` | `true` | Enable HTTPS |
| `LOG_CONFIG_FILE` | `/opt/gluesync/shared/logback.xml` | Logging config |
| `ADMIN_PASS` | `<ADMIN_PASSWORD>` | Admin password |

## Automator Configuration

### Hardcoded Settings
The Automator binary has these hardcoded values:
- **Core Hub URL**: `https://localhost:1717`
- **SSL Verification**: Enabled (can be disabled via UI)

### Network Requirements
Since Automator uses `localhost:1717`, both services must run on the same host.

### Running Automator
```bash
cd ~/gluesync-automator
./gluesync-automator \
  --no-open-browser \
  --host 0.0.0.0 \
  --port 9090
```

### Command Line Options
| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Bind interface |
| `--port` | `8080` | Listen port |
| `--no-open-browser` | - | Disable browser auto-open |
| `--log-level` | `info` | Logging level |

## Access URLs

### After Configuration
| Service | URL | Protocol |
|---------|-----|----------|
| Core Hub UI | https://192.168.13.53:1717/ui/index.html | HTTPS |
| Core Hub API | https://192.168.13.53:1717 | HTTPS |
| Automator UI | http://192.168.13.53:9090 | HTTP |
| Automator API | http://192.168.13.53:9090/api | HTTP |

## Automator API Endpoints

### Authentication
- `POST /api/login` - Authenticate with Core Hub
- `POST /api/logout` - Logout
- `GET /api/state` - Get current state

### Pipeline Operations
- `GET /api/pipelines` - List all pipelines
- `GET /api/pipeline/{id}/agents` - Get pipeline agents
- `POST /api/duplicate` - Duplicate pipeline

### Bulk Operations
- `GET /api/bulk/schemas` - List schemas
- `GET /api/bulk/tables` - List tables
- `POST /api/bulk/template` - Generate entity template

### Import/Export
- `POST /api/import/all` - Import all pipelines
- `GET /api/export/all-pipelines` - Export all pipelines
- `POST /api/upload` - Upload YAML configuration

### Execution
- `POST /api/run` - Start pipeline run
- `GET /api/run/current` - Get current run status

### System
- `GET /api/healthz` - Health check
- `GET /api/version` - Version information

## Login Request Format
```json
{
  "baseUrl": "https://192.168.13.53:1717",
  "username": "admin",
  "password": "<ADMIN_PASSWORD>",
  "useSsl": true,
  "skipVerify": false,
  "enableScheduling": true,
  "createTables": true
}
```

## Troubleshooting

### Issue: Automator cannot connect to Core Hub
**Cause**: Automator uses `https://localhost:1717` but Core Hub runs on different IP
**Solution**: Both must run on same host with Core Hub using SSL

### Issue: SSL certificate verification fails
**Solution**: Set `skipVerify: true` in login request

### Issue: Port 1717 already in use
**Solution**: Stop existing Core Hub container before starting SSL version

## Files and Locations

### Automator
- **Binary**: `~/gluesync-automator/gluesync-automator`
- **Runtime**: Headless mode (PyQt6 not available)

### Core Hub Data
- **Compose**: `/home/ubuntu/molo17/DB2-MSS_53e4/gluesync-docker/`
- **Data**: `./data/`
- **Shared**: `./shared/`
- **Logs**: `./logs/`

## Related Documentation
- Core Hub API: `/pipelines` endpoint (not `/api/v1/pipelines`)
- Authentication: `/authentication/login`
- Agent Provisioning: Requires Maven access (UI recommended)

# GlueSync CLI Tool

A comprehensive command-line interface and automation toolkit for managing GlueSync pipelines, agents, and entities.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup and Installation](#setup-and-installation)
- [Configuration](#configuration)
- [Build](#build)
- [Usage](#usage)
- [API Capture](#api-capture)
- [Reference](#reference)

---

## Project Overview

This project provides:

1. **GlueSync CLI** - A command-line interface for pipeline management
2. **MITM Proxy Setup** - API capture and reverse engineering tools
3. **Containerized Deployment** - Docker/Podman support with Makefile automation
4. **Secure Configuration** - Externalized credentials and environment-based config

### Features

- Pipeline CRUD operations (create, read, update, delete)
- Agent provisioning and configuration
- Entity management (add, start, stop, monitor)
- Schema/table discovery
- Runtime operations (start, stop, status)
- API capture for reverse engineering
- Containerized deployment

---

## Architecture

### Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          INTERNET                                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
        ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  MITM Proxy  │ │   Core Hub   │ │   Traefik    │ │   Traefik    │
│   Port 1716  │ │   Port 1717  │ │   Port 8080  │ │   Port 8443  │
│  (Capture)   │ │   (Direct)   │ │    (HTTP)    │ │   (HTTPS)    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │   Services   │
                   │  (Chronos,   │
                   │  Grafana,    │
                   │  Prometheus) │
                   └──────────────┘
```

### Port Usage

| Port | Service | Purpose |
|------|---------|---------|
| 1716 | MITM Proxy | API capture mode |
| 1717 | Core Hub | Direct access |
| 8080 | Traefik | HTTP access |
| 8443 | Traefik | HTTPS access |
| 9090 | GlueSync Automator | Automation UI |

---

## Project Structure

```
/home/ubuntu/_qoder/
├── gluesync_cli.py              # Legacy CLI (v1)
├── gluesync_cli_v2.py           # New kubectl-style CLI (v2)
├── config.json                  # Non-sensitive configuration
├── .env                         # Credentials (not in git)
├── .env.example                 # Credentials template
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
│
├── Dockerfile                   # Production container image
├── Dockerfile.dev               # Development container image
├── docker-compose.yml           # Compose configuration
├── Makefile                     # Build automation
│
├── capture_api.py               # MITM proxy capture script
├── start-mitm-capture.sh        # Start MITM for API capture
├── core-hub-mitm.sh             # Full MITM setup script
│
├── scripts/
│   ├── build.sh                 # Container build script
│   └── tcp-proxy.py             # TCP port forwarder
│
├── systemd/                     # Systemd service files
├── data/                        # Data directory for exports
│
├── API_CAPTURE_SUMMARY.md       # Captured API documentation
├── MITM_SETUP.md                # MITM setup guide
├── AUTOMATOR_SETUP.md           # Automator setup guide
└── README.md                    # This file
```

---

## Prerequisites

### System Requirements

- Ubuntu 22.04 (or compatible Linux distribution)
- Python 3.11+
- Podman or Docker
- podman-compose or docker-compose

### Install Dependencies

```bash
# Python dependencies
pip3 install -r requirements.txt

# Or use container (recommended)
make build
```

---

## Setup and Installation

### 1. Clone and Navigate

```bash
cd /home/ubuntu/_qoder
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required variables in .env:**
```bash
GLUESYNC_ADMIN_USERNAME=admin
GLUESYNC_ADMIN_PASSWORD=<your_password>
AS400_USERNAME=<as400_user>
AS400_PASSWORD=<as400_pass>
MSSQL_USERNAME=<mssql_user>
MSSQL_PASSWORD=<mssql_pass>
```

### 3. Configure Settings

Edit `config.json` for your environment:

```json
{
  "core_hub": {
    "base_url": "https://192.168.13.53:1717",
    "verify_ssl": false
  },
  "pipeline": {
    "name": "AS400-to-MSSQL-Pipeline",
    "description": "Sync data from AS400 DB2 to Microsoft SQL Server"
  },
  "source_agent": {
    "agent_internal_name": "ibm-iseries",
    "connection": {
      "host": "161.82.146.249",
      "database_name": "GSLIBTST"
    }
  },
  "target_agent": {
    "agent_internal_name": "mssql-cdc",
    "connection": {
      "host": "192.168.13.62",
      "database_name": "GSTargetDB"
    }
  }
}
```

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GLUESYNC_ADMIN_USERNAME` | Core Hub admin username | Yes |
| `GLUESYNC_ADMIN_PASSWORD` | Core Hub admin password | Yes |
| `AS400_USERNAME` | AS400 database username | For source agents |
| `AS400_PASSWORD` | AS400 database password | For source agents |
| `MSSQL_USERNAME` | MSSQL database username | For target agents |
| `MSSQL_PASSWORD` | MSSQL database password | For target agents |

### Configuration Files

| File | Purpose | Sensitive |
|------|---------|-----------|
| `.env` | Credentials | Yes |
| `config.json` | Hosts, ports, agent types | No |

---

## Build

### Using Make (Recommended)

```bash
# Show all available commands
make help

# Build container image
make build

# Run CLI with default command
make run

# Execute specific command
make exec CMD="pipeline list"

# Start interactive shell
make shell

# Clean up containers and images
make clean
```

### Using Scripts

```bash
# Build with script
./scripts/build.sh
```

### Using Podman/Docker Directly

```bash
# Build
podman build -t gluesync-cli:latest -f Dockerfile .

# Run
podman run --rm \
  -v $(pwd)/config.json:/app/config/config.json:ro \
  -v $(pwd)/.env:/app/config/.env:ro \
  gluesync-cli:latest pipeline list
```

---

## Usage

### CLI Commands (v2 - kubectl-style)

The CLI uses a resource-action pattern similar to kubectl:

```bash
gluesync-cli <action> <resource> [id] --flags
```

#### Pipeline Management

```bash
# List pipelines
gluesync-cli get pipelines

# Get pipeline details
gluesync-cli get pipeline <pipeline-id>

# Create pipeline
gluesync-cli create pipeline --name "My Pipeline" --description "Description"

# Delete pipeline
gluesync-cli delete pipeline <pipeline-id>
```

#### Entity Management

```bash
# List entities in pipeline
gluesync-cli get entities --pipeline <pipeline-id>

# Get entity details
gluesync-cli get entity <entity-id> --pipeline <pipeline-id>

# Update entity write method
gluesync-cli update entity <entity-id> --pipeline <pipeline-id> --write-method UPSERT

# Start entity with snapshot
gluesync-cli start entity <entity-id> --pipeline <pipeline-id> --with-snapshot

# Stop entity
gluesync-cli stop entity <entity-id> --pipeline <pipeline-id>
```

#### Agent Management

```bash
# List available agent types
gluesync-cli get agent-types

# List agents in pipeline
gluesync-cli get agents --pipeline <pipeline-id>

# Provision agent
gluesync-cli create agent --pipeline <pipeline-id> \
  --type source \
  --agent-type ibm-iseries \
  --tag "my-as400-source"

# Configure agent credentials
gluesync-cli configure agent <agent-id> --pipeline <pipeline-id> \
  --host 161.82.146.249 \
  --database GSLIBTST \
  --username <user> \
  --password <pass>
```

#### Discovery

```bash
# List schemas
gluesync-cli get schemas --pipeline <pipeline-id> --agent <agent-id>

# List tables
gluesync-cli get tables --pipeline <pipeline-id> --agent <agent-id> --schema GSLIBTST

# List columns
gluesync-cli get columns --pipeline <pipeline-id> --agent <agent-id> --schema GSLIBTST --table CUSTOMERS
```

#### Output Formats

```bash
# JSON output
gluesync-cli get pipelines --output json
gluesync-cli get entities --pipeline 8aeb9fb6 -o json
```

### Legacy CLI (v1)

The original CLI is still available as `gluesync_cli.py`:

```bash
python3 gluesync_cli.py pipeline list
python3 gluesync_cli.py entity list <pipeline-id>
```

### Using Container Alias

```bash
# Set alias (add to ~/.bashrc)
alias gluesyncli='podman run --rm \
  -v /home/ubuntu/_qoder/config.json:/app/config/config.json:ro \
  -v /home/ubuntu/_qoder/.env:/app/config/.env:ro \
  gluesync-cli:latest'

# Use alias
gluesyncli pipeline list
gluesyncli agent types
```

---

## API Capture

### When to Use

Use MITM proxy when you need to:
- Reverse engineer GlueSync APIs
- Capture new API endpoints
- Debug API calls
- Document API behavior

### Setup

```bash
# 1. Ensure Core Hub is running on port 1717
podman-compose up -d gluesync-core-hub

# 2. Start MITM capture
./start-mitm-capture.sh

# 3. Access via MITM port (1716) for capture
https://localhost:1716/ui/index.html

# 4. Perform actions in UI

# 5. Stop MITM (Ctrl+C) when done
```

### Capture Files

| File | Description |
|------|-------------|
| `captured_api_calls.json` | All captured API calls |
| `capture_api.py` | MITM addon script |

### Viewing Captured Data

```bash
# List all captured endpoints
cat captured_api_calls.json | python3 -c "
import json,sys
data=json.load(sys.stdin)
for d in data:
    print(f\"{d['method']:6} {d['path']}\")
"
```

---

## Reference

### Available Agent Types

| Name | Internal Name | Role |
|------|---------------|------|
| IBM iSeries (AS400) | `ibm-iseries` | source |
| Microsoft SQL Server (CDC) | `mssql-cdc` | target |
| Oracle | `oracle` | both |
| PostgreSQL | `postgresql` | both |
| MySQL | `mysql` | both |
| MongoDB | `mongodb` | both |

### API Endpoints (Captured)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/authentication/login` | Authenticate |
| GET | `/pipelines` | List pipelines |
| POST | `/pipelines` | Create pipeline |
| GET | `/pipelines/{id}` | Get pipeline |
| DELETE | `/pipelines/{id}` | Delete pipeline |
| GET | `/pipelines/{id}/agents` | List agents |
| GET | `/pipelines/{id}/agents/add` | Provision agent |
| PUT | `/pipelines/{id}/agents/{agentId}` | Assign agent |
| PUT | `/pipelines/{id}/agents/{agentId}/config/credentials` | Configure credentials |
| GET | `/pipelines/{id}/entities` | List entities |
| PUT | `/pipelines/{id}/config/entities` | Create entity |
| POST | `/pipelines/{id}/commands/sync/redo` | Start entity |
| POST | `/pipelines/{id}/commands/sync/stop` | Stop entity |

### Troubleshooting

#### Port Already in Use
```bash
# Check what's using the port
sudo ss -tlnp | grep 1717

# Stop conflicting service
podman stop <container-name>
```

#### Authentication Failed
```bash
# Check credentials in .env
cat .env

# Verify config.json
cat config.json
```

#### Agent Provisioning Failed
- Ensure Core Hub has Maven repository access
- Check `bootstrap-core-hub.json` is mounted
- Verify network connectivity

### Related Documentation

- `API_CAPTURE_SUMMARY.md` - Detailed API documentation
- `MITM_SETUP.md` - MITM proxy setup guide
- `AUTOMATOR_SETUP.md` - Automator configuration

---

## License

This project is for internal use with GlueSync integration.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review captured API calls
3. Verify configuration files
4. Check container logs: `podman logs <container-name>`

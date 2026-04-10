# GlueSync CLI

GlueSync lifecycle management via CLI - manage pipelines, agents, and entities through the Core Hub API.

## Quick Start

```bash
# Set credentials
export GLUESYNC_ADMIN_PASSWORD='P@ssw0rd'

# Run CLI
./gluesync_cli_v2.py get pipelines
./gluesync_cli_v2.py agents 32c1dc34
./gluesync_cli_v2.py maintenance exit 32c1dc34
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md)** | **Complete workflow examples, interactive vs automated modes, internal automation details** |
| [gluesync_cli_design.md](gluesync_cli_design.md) | CLI architecture and design decisions |
| [proxy/MITM_PROXY.md](proxy/MITM_PROXY.md) | MITM proxy setup and API capture |
| [proxy/API_CAPTURE_SUMMARY.md](proxy/API_CAPTURE_SUMMARY.md) | Captured API endpoints reference |

## 🚀 Quick Commands

### Pipeline Management
```bash
./gluesync_cli_v2.py get pipelines
./gluesync_cli_v2.py get pipeline 32c1dc34
./gluesync_cli_v2.py create pipeline --name "My Pipeline"
./gluesync_cli_v2.py delete pipeline 32c1dc34
```

### Entity Management
```bash
./gluesync_cli_v2.py get entities --pipeline 32c1dc34
./gluesync_cli_v2.py get entity a53b7c28 --pipeline 32c1dc34
./gluesync_cli_v2.py create entity --pipeline 32c1dc34 \
  --source-library GSLIBTST --source-table CUSTOMERS \
  --target-schema dbo --target-table customers
./gluesync_cli_v2.py delete entity a53b7c28 --pipeline 32c1dc34
```

### Agent & Schema Discovery
```bash
./gluesync_cli_v2.py agents 32c1dc34
./gluesync_cli_v2.py discover-schema 32c1dc34 \
  --agent-id d74fad4b --library GSLIBTST --table CUSTOMERS2
```

### Maintenance Mode
```bash
./gluesync_cli_v2.py maintenance enter 32c1dc34
# Make configuration changes
./gluesync_cli_v2.py maintenance exit 32c1dc34
```

### Start/Stop Replication
```bash
./gluesync_cli_v2.py start a53b7c28 --pipeline 32c1dc34 --mode snapshot
./gluesync_cli_v2.py stop a53b7c28 --pipeline 32c1dc34
```

## Key Files

| File | Description |
|------|-------------|
| `gluesync_cli_v2.py` | kubectl-style CLI |
| `Dockerfile` | Container image |
| `Makefile` | Build automation |
| `proxy/` | MITM proxy for API capture |

## Proxy / API Capture

The `proxy/` folder contains tools for capturing and analyzing GlueSync API calls:

```bash
cd proxy
./start-mitm-capture.sh    # Start MITM proxy on port 1716
./core-hub-mitm.sh         # Start Core Hub with MITM capture
```

See `proxy/MITM_PROXY.md` for detailed documentation.

## Configuration

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
# Edit .env with your Core Hub URL and credentials
```

## Related Projects

| Project | Repository | Purpose |
|---------|-----------|---------|
| **qadmcli** | https://github.com/pnandasa-aide/qadmcli | AS400/MSSQL database management |
| **replica-mon** | https://github.com/pnandasa-aide/replica-mon | Replication monitoring |

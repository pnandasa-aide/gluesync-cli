# GlueSync CLI

GlueSync lifecycle management via CLI - manage pipelines, agents, and entities through the Core Hub API.

## Quick Start

```bash
# Build container
make build

# Run CLI
make run CMD="get pipelines"

# Or run directly
./gluesync_cli_v2.py get pipelines
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

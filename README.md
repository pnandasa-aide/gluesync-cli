# GlueSync Automation Projects

Monorepo containing three related projects for database replication management.

## Projects

### 1. gluesync-cli/
**GlueSync lifecycle management via CLI**

Manage GlueSync pipelines, agents, and entities through the Core Hub API.

```bash
cd gluesync-cli
make build
make run CMD="get pipelines"
```

**Key Files:**
- `gluesync_cli_v2.py` - kubectl-style CLI
- `Dockerfile` - Container image
- `Makefile` - Build automation

---

### 2. qadmcli/
**Database management for AS400 and MSSQL**

Originally from https://github.com/pnandasa-aide/qadmcli.git

Manage databases, tables, users, and read journal entries.

```bash
cd qadmcli
./qadmcli.sh journal entries -n CUSTOMERS -l GSLIBTST
```

**Key Files:**
- `src/qadmcli/` - Python package
- `Containerfile` - Podman image
- `qadmcli.sh` - Helper script

---

### 3. replica-mon/
**Replication monitoring and reconciliation**

Monitor replication progress and compare source vs target data.

```bash
cd replica-mon
./cli.py compare --pipeline 8aeb9fb6 --entity 98fd97b8 --since "2025-04-09 10:00:00"
```

**Key Files:**
- `cli.py` - Main CLI
- `lib/` - Shared libraries
- `scripts/` - Helper scripts

## Project Relationships

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   qadmcli       │     │  gluesync-cli   │     │  replica-mon    │
│                 │     │                 │     │                 │
│  AS400 Journal  │◄────│  Entity Mapping │────►│  Compare &      │
│  MSSQL CT/CDC   │     │  Pipeline API   │     │  Reconcile      │
│  DB Management  │     │  Lifecycle      │     │  Monitor        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                                               ▲
        │                                               │
        └──────────────────┬────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │   AS400     │
                    │   MSSQL     │
                    │   GlueSync  │
                    └─────────────┘
```

## Quick Start

```bash
# 1. Build all projects
make -C gluesync-cli build
make -C qadmcli build

# 2. Configure credentials
cp .env.example .env
# Edit .env with your credentials

# 3. Test connections
cd gluesync-cli && ./gluesync_cli_v2.py get pipelines
cd qadmcli && ./qadmcli.sh connection test
cd replica-mon && ./cli.py --help
```

## Git Structure

This is a single git repository with three project folders. Each folder can be extracted to its own repo later if needed.

```
_qoder/
├── .git/                 # Single git repo for all projects
├── .env                  # Shared credentials (not in git)
├── gluesync-cli/         # GlueSync CLI project
├── qadmcli/              # Database management project
├── replica-mon/          # Replication monitoring project
└── README.md             # This file
```

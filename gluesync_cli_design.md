# GlueSync CLI Design Specification

## Overview
A comprehensive command-line interface for managing GlueSync pipelines, agents, and entities.

## Architecture

```
gluesync-cli/
├── gluesync_cli.py          # Main entry point
├── commands/
│   ├── __init__.py
│   ├── pipeline.py          # Pipeline CRUD operations
│   ├── agent.py             # Agent management
│   ├── entity.py            # Entity management
│   ├── runtime.py           # Start/stop/resume operations
│   └── discovery.py         # Schema/table discovery
├── core/
│   ├── __init__.py
│   ├── client.py            # API client
│   ├── config.py            # Configuration management
│   └── auth.py              # Authentication
└── utils/
    ├── __init__.py
    ├── formatters.py        # Output formatting
    └── validators.py        # Input validation
```

## Command Structure

```bash
gluesync-cli [global-options] <command> [subcommand] [options]
```

### Global Options
- `--config, -c` - Path to config file (default: ./config.json)
- `--env, -e` - Path to .env file (default: ./.env)
- `--output, -o` - Output format: table|json|yaml (default: table)
- `--verbose, -v` - Verbose output
- `--help, -h` - Show help

## Commands

### 1. Pipeline Management

#### List Pipelines
```bash
gluesync-cli pipeline list [options]
```
Options:
- `--filter, -f` - Filter by name/description
- `--status` - Filter by status: active|inactive|error
- `--all, -a` - Include deleted pipelines

Output:
```
ID          NAME                    STATUS    AGENTS    ENTITIES    CREATED
----------  ----------------------  --------  --------  ----------  -------------------
b2f6e46a    1st pipeline            active    2/2       1           2026-04-08 12:35:00
986c7488    AS400-to-MSSQL          inactive  0/2       0           2026-04-08 11:20:00
```

#### Create Pipeline
```bash
gluesync-cli pipeline create --name "My Pipeline" [--description "..."] [--config-file pipeline-config.json]
```
Interactive mode (if no config-file):
```bash
gluesync-cli pipeline create --interactive
# Prompts for:
# - Pipeline name
# - Description
# - Source agent type (ibm-iseries, oracle, postgresql, etc.)
# - Target agent type (mssql-cdc, postgresql, etc.)
# - Source connection details
# - Target connection details
```

#### Get Pipeline Details
```bash
gluesync-cli pipeline get <pipeline-id> [options]
```
Options:
- `--include-agents` - Include agent details
- `--include-entities` - Include entity details
- `--include-config` - Include full configuration

Output:
```json
{
  "id": "b2f6e46a",
  "name": "1st pipeline",
  "description": "",
  "status": "active",
  "configurationCompleted": true,
  "agents": {
    "source": {
      "id": "00c7ac81",
      "type": "ibm-iseries",
      "status": "connected",
      "host": "161.82.146.249"
    },
    "target": {
      "id": "92de6be5",
      "type": "mssql-cdc",
      "status": "connected",
      "host": "192.168.13.62"
    }
  },
  "entities": [
    {
      "name": "GSLIBTST.CUSTOMERS",
      "status": "running",
      "recordsProcessed": 15234
    }
  ]
}
```

#### Update Pipeline
```bash
gluesync-cli pipeline update <pipeline-id> --name "New Name" [--description "..."]
```

#### Delete Pipeline
```bash
gluesync-cli pipeline delete <pipeline-id> [--force, -f]
```

#### Clone/Duplicate Pipeline
```bash
gluesync-cli pipeline clone <pipeline-id> --name "New Pipeline Name"
```

---

### 2. Agent Management

#### List Agents
```bash
gluesync-cli agent list <pipeline-id>
```
Output:
```
AGENT ID    TYPE           ROLE     STATUS       HOST
----------  -------------  -------  -----------  ----------------
00c7ac81    ibm-iseries    source   connected    161.82.146.249
92de6be5    mssql-cdc      target   connected    192.168.13.62
```

#### Provision Agent
```bash
gluesync-cli agent provision <pipeline-id> \
  --type source|target \
  --agent-type ibm-iseries|mssql-cdc|oracle|... \
  --tag "my-agent-tag"
```

#### Configure Agent Credentials
```bash
gluesync-cli agent configure <pipeline-id> <agent-id> \
  --host <host> \
  --port <port> \
  --database <dbname> \
  --username <user> \
  --password <pass> \
  [--trust-cert]
```

Interactive mode:
```bash
gluesync-cli agent configure <pipeline-id> <agent-id> --interactive
```

#### Test Agent Connection
```bash
gluesync-cli agent test <pipeline-id> <agent-id>
```
Output:
```
Testing connection to agent 00c7ac81...
✓ Host reachable
✓ Authentication successful
✓ Database accessible
✓ CDC enabled
```

#### Remove Agent
```bash
gluesync-cli agent remove <pipeline-id> <agent-id> [--force]
```

---

### 3. Entity Management

#### List Entities
```bash
gluesync-cli entity list <pipeline-id> [options]
```
Options:
- `--status` - Filter by status: running|stopped|error|syncing
- `--group` - Filter by group

Output:
```
ENTITY NAME          SOURCE TABLE       TARGET TABLE       STATUS    LAST SYNC
-------------------  -----------------  -----------------  --------  -------------------
GSLIBTST.CUSTOMERS   GSLIBTST.CUSTOMERS dbo.CUSTOMERS      running   2026-04-08 14:30:00
GSLIBTST.ORDERS      GSLIBTST.ORDERS    dbo.ORDERS         stopped   2026-04-08 12:00:00
```

#### Add Entity
```bash
gluesync-cli entity add <pipeline-id> \
  --source-schema GSLIBTST \
  --source-table CUSTOMERS \
  --target-schema dbo \
  --target-table CUSTOMERS \
  [--group default]
```

Interactive mode with discovery:
```bash
gluesync-cli entity add <pipeline-id> --interactive
# Shows available tables from source, prompts for selection,
# then shows target schema options
```

#### Get Entity Status
```bash
gluesync-cli entity status <pipeline-id> <entity-name>
```
Output:
```json
{
  "entityName": "GSLIBTST.CUSTOMERS",
  "status": "running",
  "source": {
    "schema": "GSLIBTST",
    "table": "CUSTOMERS",
    "recordsTotal": 50000,
    "recordsProcessed": 15234,
    "lastChange": "2026-04-08T14:30:00Z"
  },
  "target": {
    "schema": "dbo",
    "table": "CUSTOMERS",
    "recordsInserted": 15234,
    "recordsUpdated": 0,
    "recordsDeleted": 0
  },
  "performance": {
    "throughput": "1500 records/sec",
    "latency": "200ms"
  }
}
```

#### Remove Entity
```bash
gluesync-cli entity remove <pipeline-id> <entity-name> [--force]
```

---

### 4. Runtime Operations

#### Start Processing
```bash
gluesync-cli runtime start <pipeline-id> [entity-name]
```
Options:
- `--entity, -e` - Specific entity to start (default: all)
- `--mode` - Start mode: cdc|snapshot|both (default: both)

Output:
```
Starting pipeline b2f6e46a...
✓ Source agent connected
✓ Target agent connected
✓ Entity GSLIBTST.CUSTOMERS started in CDC mode
✓ Pipeline running
```

#### Stop Processing
```bash
gluesync-cli runtime stop <pipeline-id> [entity-name] [--force]
```

#### Pause/Resume
```bash
gluesync-cli runtime pause <pipeline-id> [entity-name]
gluesync-cli runtime resume <pipeline-id> [entity-name]
```

#### Get Runtime Status
```bash
gluesync-cli runtime status <pipeline-id> [options]
```
Options:
- `--watch, -w` - Continuous monitoring (like top)
- `--interval` - Refresh interval in seconds (default: 5)

Output:
```
Pipeline: b2f6e46a (1st pipeline)
Status: RUNNING
Uptime: 2h 30m

Entity                    Status    Records/sec    Lag    Errors
------------------------  --------  -------------  -----  ------
GSLIBTST.CUSTOMERS        syncing   1,500          200ms  0
GSLIBTST.ORDERS           running   800            150ms  0
```

#### Restart Pipeline
```bash
gluesync-cli runtime restart <pipeline-id> [--mode cdc|snapshot|both]
```

---

### 5. Discovery Commands

#### List Schemas
```bash
gluesync-cli discovery schemas <pipeline-id> --agent <agent-id>
```

#### List Tables
```bash
gluesync-cli discovery tables <pipeline-id> --agent <agent-id> --schema <schema-name>
```

#### List Columns
```bash
gluesync-cli discovery columns <pipeline-id> --agent <agent-id> --schema <schema> --table <table>
```

#### Search Tables
```bash
gluesync-cli discovery search <pipeline-id> --pattern "CUST*" [--agent source|target]
```

---

### 6. Bulk Operations

#### Bulk Add Entities
```bash
gluesync-cli bulk add-entities <pipeline-id> --file entities-list.txt
```
File format (one per line):
```
GSLIBTST.CUSTOMERS:dbo.CUSTOMERS
GSLIBTST.ORDERS:dbo.ORDERS
GSLIBTST.PRODUCTS:dbo.PRODUCTS
```

#### Export Configuration
```bash
gluesync-cli bulk export <pipeline-id> --file pipeline-backup.json
```

#### Import Configuration
```bash
gluesync-cli bulk import --file pipeline-backup.json [--new-name "Restored Pipeline"]
```

---

### 7. Monitoring & Logs

#### View Logs
```bash
gluesync-cli logs <pipeline-id> [options]
```
Options:
- `--entity` - Filter by entity
- `--level` - Log level: info|warn|error|debug
- `--follow, -f` - Follow logs (tail -f style)
- `--since` - Show logs since (e.g., "1h", "30m", "2026-04-08 12:00")
- `--tail` - Show last N lines

#### Get Metrics
```bash
gluesync-cli metrics <pipeline-id> [entity-name] [options]
```
Options:
- `--type` - Metric type: throughput|latency|errors|all
- `--period` - Time period: 1h|6h|24h|7d

---

## API Coverage Status

### ✅ Implemented (from capture)
- [x] Authentication (`POST /authentication/login`)
- [x] List pipelines (`GET /pipelines`)
- [x] Create pipeline (`POST /pipelines`)
- [x] Get pipeline (`GET /pipelines/{id}`)
- [x] Update pipeline (`PUT /pipelines/{id}`)
- [x] Delete pipeline (`DELETE /pipelines/{id}`)
- [x] Provision agent (`GET /pipelines/{id}/agents/add`)
- [x] Assign agent (`PUT /pipelines/{id}/agents/{agentId}`)
- [x] Configure agent credentials (`PUT /.../config/credentials`)
- [x] Configure agent specific (`PUT /.../config/specific`)
- [x] List entities (`GET /pipelines/{id}/entities`)
- [x] Create entity (`PUT /pipelines/{id}/config/entities`)
- [x] Discovery APIs (`GET /.../discovery/schemas|tables|columns`)

### ❓ Need Capture (Unknown APIs)
- [ ] Start/stop entity processing
- [ ] Get entity runtime status
- [ ] Pause/resume operations
- [ ] Get pipeline runtime status
- [ ] View logs
- [ ] Get metrics

### 🔍 Capture Required
To implement runtime operations, we need to capture:
1. Start processing API calls
2. Stop processing API calls
3. Status monitoring APIs
4. Log retrieval APIs

---

## Implementation Priority

### Phase 1: Core CRUD (Week 1)
- Pipeline CRUD operations
- Agent provisioning and configuration
- Basic entity management

### Phase 2: Discovery & Bulk (Week 2)
- Schema/table discovery
- Bulk operations
- Import/export

### Phase 3: Runtime & Monitoring (Week 3)
- Start/stop/resume operations
- Status monitoring
- Logs and metrics

---

## Configuration File Format

### ~/.gluesync-cli/config.yaml
```yaml
default:
  core_hub_url: https://192.168.13.53:1717
  verify_ssl: false
  output_format: table
  
environments:
  production:
    core_hub_url: https://prod-gluesync.company.com:1717
    verify_ssl: true
    
  staging:
    core_hub_url: https://staging-gluesync.company.com:1717
    verify_ssl: false
```

---

## Error Handling

All commands should return appropriate exit codes:
- `0` - Success
- `1` - General error
- `2` - Invalid arguments
- `3` - Authentication failed
- `4` - Resource not found
- `5` - API error (with message from server)

Error output format:
```json
{
  "error": true,
  "code": "PIPELINE_NOT_FOUND",
  "message": "Pipeline with ID 'abc123' not found",
  "suggestion": "Use 'gluesync-cli pipeline list' to see available pipelines"
}
```

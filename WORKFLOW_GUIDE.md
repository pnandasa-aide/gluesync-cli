# GlueSync CLI Workflow Guide

Complete guide for managing GlueSync replication pipelines, entities, and agents using the CLI tools.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Prerequisites](#prerequisites)
3. [Interactive vs Automated Workflows](#interactive-vs-automated-workflows)
4. [Complete Workflow Examples](#complete-workflow-examples)
5. [Internal Automation Details](#internal-automation-details)
6. [Troubleshooting](#troubleshooting)

---

## Quick Reference

```bash
# Environment setup
export GLUESYNC_ADMIN_PASSWORD='<your_password_here>'

# Core commands
python3 gluesync_cli_v2.py get pipelines
python3 gluesync_cli_v2.py get entities --pipeline <ID>
python3 gluesync_cli_v2.py agents <pipeline_id>
python3 gluesync_cli_v2.py maintenance exit <pipeline_id>
python3 gluesync_cli_v2.py discover-schema <pipeline_id> --agent-id <ID> --library GSLIBTST --table CUSTOMERS
```

---

## Prerequisites

### 1. Environment Configuration

```bash
# Required environment variable
export GLUESYNC_ADMIN_PASSWORD='your_password'

# Or create .env file
cp .env.example .env
# Edit .env with your credentials
```

### 2. GlueSync Services Running

```bash
# Start GlueSync stack
cd ~/molo17/DB2-MSS_53e4/gluesync-docker
./start-gluesync.sh

# Verify Core Hub is accessible
curl -k https://localhost:1717/ui/ | head -3
```

### 3. Agents Configured

Before creating entities, ensure source and target agents are configured via UI:
1. Access Core Hub UI: `https://localhost:1717/ui/`
2. Navigate to Pipeline → Agents
3. Configure source agent (AS400/DB2) with credentials
4. Configure target agent (MSSQL) with credentials
5. Test connections for both agents

---

## Interactive vs Automated Workflows

### When to Use Interactive Mode

Use **interactive mode** when:
- You don't know the exact table schema
- You need to verify table structure before creating entity
- You're exploring available tables
- First-time setup

### When to Use Automated Mode

Use **automated mode** when:
- You know all required parameters (schema, table, columns, keys)
- Repetitive/entity bulk operations
- Scripted/CI/CD workflows
- Schema YAML files are available

---

## Complete Workflow Examples

### Workflow 1: Add New Table (Interactive - Unknown Schema)

This workflow discovers the schema automatically before creating the entity.

```bash
#!/bin/bash
# interactive_add_entity.sh

PIPELINE_ID="32c1dc34"
SOURCE_LIBRARY="GSLIBTST"
SOURCE_TABLE="CUSTOMERS2"
TARGET_SCHEMA="dbo"
TARGET_TABLE="customers2"

echo "=== Step 1: Check pipeline status ==="
python3 gluesync_cli_v2.py get pipelines

echo ""
echo "=== Step 2: Exit maintenance mode (if active) ==="
python3 gluesync_cli_v2.py maintenance exit $PIPELINE_ID

echo ""
echo "=== Step 3: Verify agents are available ==="
python3 gluesync_cli_v2.py agents $PIPELINE_ID

# Capture agent IDs from output
echo ""
echo "Please note the Source and Target Agent IDs from above"
read -p "Enter Source Agent ID: " SOURCE_AGENT_ID
read -p "Enter Target Agent ID: " TARGET_AGENT_ID

echo ""
echo "=== Step 4: Discover source table schema ==="
python3 gluesync_cli_v2.py discover-schema $PIPELINE_ID \
  --agent-id $SOURCE_AGENT_ID \
  --library $SOURCE_LIBRARY \
  --table $SOURCE_TABLE

echo ""
echo "=== Step 5: Create target table on MSSQL (if not exists) ==="
# Use qadmcli to create target table
cd ~/qadmcli
./qadmcli.sh mssql execute -q "
CREATE TABLE $TARGET_SCHEMA.$TARGET_TABLE (
    -- Add columns based on discovered schema
    CUSTOMER_ID int NOT NULL,
    FIRST_NAME varchar(50) NOT NULL,
    -- ... other columns
    CONSTRAINT PK_$TARGET_TABLE PRIMARY KEY (CUSTOMER_ID)
)
"
cd ~/gluesync-cli

echo ""
echo "=== Step 6: Create entity with schema ==="
# NOTE: You'll need to manually construct the entity payload with the discovered schema
# Or use the UI for complex schemas
python3 gluesync_cli_v2.py create entity \
  --pipeline $PIPELINE_ID \
  --source-library $SOURCE_LIBRARY \
  --source-table $SOURCE_TABLE \
  --target-schema $TARGET_SCHEMA \
  --target-table $TARGET_TABLE \
  --polling-interval 500 \
  --batch-size 1000

echo ""
echo "=== Step 7: Verify entity created ==="
python3 gluesync_cli_v2.py get entities --pipeline $PIPELINE_ID
```

### Workflow 2: Add New Table (Automated - Known Schema)

Use when you have the schema definition (e.g., from qadmcli YAML files).

```bash
#!/bin/bash
# automated_add_entity.sh

PIPELINE_ID="32c1dc34"

# Known schema from qadmcli/schemas/subscriber.yaml
SOURCE_LIBRARY="GSLIBTST"
SOURCE_TABLE="SUBSCRIBER"
TARGET_SCHEMA="dbo"
TARGET_TABLE="subscriber"

echo "=== Automated Entity Creation ==="
echo "Pipeline: $PIPELINE_ID"
echo "Source: $SOURCE_LIBRARY.$SOURCE_TABLE"
echo "Target: $TARGET_SCHEMA.$TARGET_TABLE"

# Step 1: Ensure not in maintenance mode
python3 gluesync_cli_v2.py maintenance exit $PIPELINE_ID 2>/dev/null || true

# Step 2: Create entity (schema must be pre-populated in the API call)
python3 gluesync_cli_v2.py create entity \
  --pipeline $PIPELINE_ID \
  --source-library $SOURCE_LIBRARY \
  --source-table $SOURCE_TABLE \
  --target-schema $TARGET_SCHEMA \
  --target-table $TARGET_TABLE

# Step 3: Verify
python3 gluesync_cli_v2.py get entities --pipeline $PIPELINE_ID
```

### Workflow 3: Start Entity Replication

```bash
#!/bin/bash
# start_replication.sh

PIPELINE_ID="32c1dc34"
ENTITY_ID="a53b7c28"  # Get from 'get entities' command

echo "=== Starting Entity Replication ==="

# Start with initial snapshot
python3 gluesync_cli_v2.py start $ENTITY_ID \
  --pipeline $PIPELINE_ID \
  --mode snapshot

# Or start CDC only (no snapshot)
# python3 gluesync_cli_v2.py start $ENTITY_ID \
#   --pipeline $PIPELINE_ID \
#   --mode cdc
```

### Workflow 4: Maintenance Mode Operations

```bash
#!/bin/bash
# maintenance_operations.sh

PIPELINE_ID="32c1dc34"

echo "=== Enter Maintenance Mode ==="
echo "This pauses all replication for safe configuration changes"
python3 gluesync_cli_v2.py maintenance enter $PIPELINE_ID

echo ""
echo "Perform your configuration changes here..."
echo "- Add/remove entities"
echo "- Update agent settings"
echo "- Modify table mappings"

echo ""
echo "=== Exit Maintenance Mode ==="
echo "This resumes all replication"
python3 gluesync_cli_v2.py maintenance exit $PIPELINE_ID
```

---

## Internal Automation Details

This section explains what the CLI scripts handle automatically behind the scenes.

### 1. Authentication & Token Management

**What happens automatically:**
```python
# In GlueSyncClient.__init__()
class GlueSyncClient:
    def __init__(self, base_url, username, password):
        # 1. Auto-login on client creation
        resp = self.session.post(f"{base_url}/authentication/login",
                                 json={"username": username, "password": password})
        
        # 2. Extract and store API token
        self.token = resp.json()["apiToken"]
        
        # 3. Create persistent session (reuses token for all requests)
        self.session = requests.Session()
```

**User impact:** You only set `GLUESYNC_ADMIN_PASSWORD` once. The CLI handles:
- Login API call
- Token extraction
- Token attachment to every request (`Authorization: Bearer <token>`)
- Session reuse (no repeated logins)

### 2. SSL/TLS Handling

**What happens automatically:**
```python
# SSL verification disabled for localhost development
urllib3.disable_warnings()
self.session.verify = False  # skip SSL cert validation
```

**Why:** Core Hub uses self-signed certificates for localhost. In production, set `verify_ssl=True`.

### 3. Agent ID Discovery

**When creating entities, the CLI:**
```python
def create_entity(self, pipeline_id, ...):
    # 1. Fetch pipeline details
    pipeline = self.get_pipeline(pipeline_id)
    
    # 2. Extract agent IDs automatically
    for agent in pipeline.get('agents', []):
        if agent.get('agentType') == 'SOURCE':
            source_agent_id = agent.get('agentId')
        elif agent.get('agentType') == 'TARGET':
            target_agent_id = agent.get('agentId')
    
    # 3. Use these IDs in entity creation payload
```

**User impact:** You don't need to know agent IDs - the CLI finds them from the pipeline.

### 4. Schema Discovery (Manual Step)

**What the `discover-schema` command does:**
```bash
python3 gluesync_cli_v2.py discover-schema <pipeline_id> \
  --agent-id <source_agent_id> \
  --library GSLIBTST \
  --table CUSTOMERS2
```

**Behind the scenes:**
```python
def get_agent_discovery_schemas(self, pipeline_id, agent_id):
    # Calls: GET /pipelines/{id}/agents/{agent_id}/discovery/schemas
    # Returns: List of schemas with tables, columns, keys, data types
    resp = self.request("GET", f"/pipelines/{pipeline_id}/agents/{agent_id}/discovery/schemas")
    return resp.json()
```

**Returns structure:**
```json
{
  "schema": "GSLIBTST",
  "tables": [
    {
      "name": "CUSTOMERS2",
      "columns": [
        {"id": 1, "name": "CUSTOMER_ID", "type": "INTEGER"},
        {"id": 2, "name": "FIRST_NAME", "type": "CHARACTER VARYING"}
      ],
      "keys": [
        {"id": 1, "name": "CUSTOMER_ID", "type": "INTEGER"}
      ]
    }
  ]
}
```

### 5. Entity Creation Payload Construction

**What the CLI builds automatically:**
```python
entity_data = {
    "entities": [{
        "entityName": "GSLIBTST.CUSTOMERS2",
        "agentEntities": [
            {
                # Source agent entity
                "agentId": "d74fad4b",  # Auto-extracted
                "table": {"schema": "GSLIBTST", "name": "CUSTOMERS2"},
                "entityType": {
                    "type": "Source",
                    "pollingIntervalMilliseconds": 500,
                    # ... other source settings
                },
                "columns": [...],  # Must be populated from schema discovery
                "keys": [...]      # Must include primary key
            },
            {
                # Target agent entity
                "agentId": "a75b0db9",  # Auto-extracted
                "table": {"schema": "dbo", "name": "customers2"},
                "entityType": {
                    "type": "Target",
                    "allowedOperations": ["INSERT", "UPDATE", "DELETE", "TRUNCATE"],
                    # ... other target settings
                },
                "columns": [...],  # Mapped from source columns
                "keys": [...]      # Same primary key
            }
        ]
    }]
}
```

**API Call:**
```
PUT /pipelines/{id}/config/entities
Content-Type: application/json
Authorization: Bearer <token>
```

### 6. Maintenance Mode Management

**Why maintenance mode exists:**
- Prevents data inconsistency during configuration changes
- Pauses all CDC and snapshot operations
- Required before adding/removing entities

**CLI commands:**
```bash
# Enter maintenance (pauses replication)
POST /pipelines/{id}/commands/maintenance/enter
Response: 202 Accepted

# Exit maintenance (resumes replication)
POST /pipelines/{id}/commands/maintenance/exit
Response: 202 Accepted
```

**When to use:**
- ✅ Adding/removing entities
- ✅ Changing agent configurations
- ✅ Modifying table mappings
- ❌ Routine monitoring (not needed)

---

## Troubleshooting

### Error: "Missing primary keys in entity"

**Cause:** Entity payload has empty `keys` array.

**Solution:**
1. Discover schema first: `python3 gluesync_cli_v2.py discover-schema ...`
2. Ensure the table has a primary key defined
3. Include keys in entity payload

### Error: "Impossible to upsert entities before database initialization"

**Cause:** Agents not configured or pipeline in maintenance mode.

**Solution:**
```bash
# 1. Exit maintenance mode
python3 gluesync_cli_v2.py maintenance exit <pipeline_id>

# 2. Verify agents exist
python3 gluesync_cli_v2.py agents <pipeline_id>

# 3. If no agents, configure them via UI first
```

### Error: "Agents not found"

**Cause:** Pipeline created but agents not provisioned.

**Solution:**
1. Access Core Hub UI: `https://localhost:1717/ui/`
2. Navigate to pipeline
3. Configure source agent (AS400 credentials)
4. Configure target agent (MSSQL credentials)
5. Test connections
6. Retry CLI commands

### Error: "Bad Gateway" on MITM Proxy

**Cause:** Core Hub container restarted but MITM proxy has stale connection.

**Solution:**
```bash
# Kill old MITM proxy
ps aux | grep mitmdump | grep -v grep | awk '{print $2}' | xargs kill

# Restart MITM proxy
cd ~/_qoder/gluesync-cli/proxy
nohup /home/ubuntu/.local/bin/mitmdump \
  -s capture_api.py \
  --mode reverse:https://localhost:1717 \
  --listen-port 1716 \
  --ssl-insecure \
  --set block_global=false > mitmdump.log 2>&1 &
```

---

## Common Workflows

| Task | Commands | Interactive/Auto |
|------|----------|------------------|
| List all pipelines | `get pipelines` | Auto |
| View entities | `get entities --pipeline ID` | Auto |
| Add table (unknown schema) | `discover-schema` → Create target table → `create entity` | Interactive |
| Add table (known schema) | `create entity` with pre-built payload | Automated |
| Start replication | `start ENTITY_ID --pipeline ID --mode snapshot` | Auto |
| Pause for changes | `maintenance enter ID` → make changes → `maintenance exit ID` | Auto |
| View agents | `agents PIPELINE_ID` | Auto |

---

## Next Steps

- See `proxy/MITM_PROXY.md` for API capture workflows
- See `gluesync_cli_design.md` for CLI architecture
- Check `~/replica-mon/demo_workflow.sh` for complete end-to-end demo

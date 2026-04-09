# GlueSync API Capture Summary

> ⚠️ **SECURITY NOTICE**: This document contains placeholder credentials marked with `< >`. 
> Replace all placeholders with actual values before use.
> - `<ADMIN_PASSWORD>` - Core Hub admin password
> - `<AS400_USERNAME>`, `<AS400_PASSWORD>` - AS400 credentials
> - `<MSSQL_USERNAME>`, `<MSSQL_PASSWORD>` - MSSQL credentials

## Pipeline Created
- **Pipeline ID**: `b2f6e46a`
- **Pipeline Name**: `1st pipeline`
- **Source Agent**: `00c7ac81` (ibm-iseries)
- **Target Agent**: `92de6be5` (mssql-cdc)
- **Entity**: `GSLIBTST.CUSTOMERS` → `dbo.CUSTOMERS`

## Complete API Flow

### 1. Authentication
```http
POST /authentication/login
```
**Request:**
```json
{
  "username": "admin",
  "password": "<ADMIN_PASSWORD>"
}
```
**Response:**
```json
{
  "apiToken": "eyJhbGciOiJIUzI1NiIs...",
  "changeRequired": false
}
```

### 2. Provision Source Agent (ibm-iseries)
```http
GET /pipelines/{pipeline_id}/agents/add?agentType=source&agentInternalName=ibm-iseries&agentUserTag={tag}
```
**Response:**
```json
{
  "agentId": "00c7ac81"
}
```

### 3. Assign Source Agent to Pipeline
```http
PUT /pipelines/{pipeline_id}/agents/{agent_id}?agentType=SOURCE
```

### 4. Configure Source Agent Credentials
```http
PUT /pipelines/{pipeline_id}/agents/{agent_id}/config/credentials
```
**Request:**
```json
{
  "hostCredentials": {
    "host": "161.82.146.249",
    "port": 0,
    "username": "<AS400_USERNAME>",
    "password": "<AS400_PASSWORD>",
    "disableAuth": false,
    "enableTls": false,
    "trustServerCertificate": false,
    "minConnectionsCount": 5,
    "maxConnectionsCount": 25
  }
}
```

### 5. Configure Source Agent Specific Settings
```http
PUT /pipelines/{pipeline_id}/agents/{agent_id}/config/specific
```
**Request:**
```json
{
  "configuration": {}
}
```

### 6. Provision Target Agent (mssql-cdc)
```http
GET /pipelines/{pipeline_id}/agents/add?agentType=target&agentInternalName=mssql-cdc&agentUserTag={tag}
```
**Response:**
```json
{
  "agentId": "92de6be5"
}
```

### 7. Assign Target Agent to Pipeline
```http
PUT /pipelines/{pipeline_id}/agents/{agent_id}?agentType=TARGET
```

### 8. Configure Target Agent Credentials
```http
PUT /pipelines/{pipeline_id}/agents/{agent_id}/config/credentials
```
**Request:**
```json
{
  "hostCredentials": {
    "host": "192.168.13.62",
    "port": 0,
    "databaseName": "GSTargetDB",
    "username": "<MSSQL_USERNAME>",
    "password": "<MSSQL_PASSWORD>",
    "disableAuth": false,
    "enableTls": false,
    "trustServerCertificate": true,
    "minConnectionsCount": 5,
    "maxConnectionsCount": 25
  }
}
```

### 9. Configure Target Agent Specific Settings
```http
PUT /pipelines/{pipeline_id}/agents/{agent_id}/config/specific
```
**Request:**
```json
{
  "configuration": {}
}
```

### 10. Schema Discovery
```http
GET /pipelines/{pipeline_id}/agents/{source_agent_id}/discovery/schemas
GET /pipelines/{pipeline_id}/agents/{target_agent_id}/discovery/schemas
GET /pipelines/{pipeline_id}/agents/{source_agent_id}/discovery/tables?schema=GSLIBTST
GET /pipelines/{pipeline_id}/agents/{target_agent_id}/discovery/tables?schema=dbo
GET /pipelines/{pipeline_id}/agents/{source_agent_id}/discovery/columns?tableschema=GSLIBTST&tablename=CUSTOMERS
GET /pipelines/{pipeline_id}/agents/{target_agent_id}/discovery/columns?tableschema=dbo&tablename=CUSTOMERS
```

### 11. Create Target Table
```http
PUT /pipelines/{pipeline_id}/config/entities/schemas/dbo/tables/CUSTOMERS/statements/create-table
```
**Request:**
```json
{
  "columns": [
    {
      "id": -4891398803227897090,
      "name": "CUST_ID",
      "type": "int",
      "isPrimaryKey": true,
      "isNullable": true,
      "dataLength": 0,
      "ordinalPosition": 1,
      "numericPrecision": 9,
      "numericScale": 0
    },
    ...
  ]
}
```

### 12. Create Entity Mapping
```http
PUT /pipelines/{pipeline_id}/config/entities/statements/create-table
```
**Request:**
```json
{
  "statement": "CREATE TABLE [dbo].[CUSTOMERS] (\n   [CUST_ID] int,\n   [FIRST_NAME] varchar(50),\n   [LAST_NAME] varchar(50),\n   [EMAIL] varchar(100),\n   [PHONE] varchar(20),\n   [CREATED_AT] datetime,\n   PRIMARY KEY (\n      [CUST_ID]\n   )\n)"
}
```

### 13. Save Entity Configuration
```http
PUT /pipelines/{pipeline_id}/config/entities
```
**Request:**
```json
{
  "entities": [
    {
      "entityName": "GSLIBTST.CUSTOMERS",
      "agentEntities": [
        {
          "type": "SingleTable",
          "entityType": {
            "type": "Source",
            "maxFetchItemsCountPerIteration": 1000,
            "maxTransactionMessageKbSize": 1024,
            "pollingIntervalMilliseconds": 500
          },
          "agentId": "00c7ac81",
          "table": {
            "schema": "GSLIBTST",
            "name": "CUSTOMERS"
          }
        },
        {
          "type": "SingleTable",
          "entityType": {
            "type": "Target",
            "allowedOperations": ["INSERT", "UPDATE", "DELETE", "TRUNCATE"]
          },
          "agentId": "92de6be5",
          "table": {
            "schema": "dbo",
            "name": "CUSTOMERS"
          }
        }
      ]
    }
  ]
}
```

### 14. Update Pipeline Name
```http
PUT /pipelines/{pipeline_id}
```
**Request:**
```json
{
  "name": "1st pipeline",
  "description": ""
}
```

## Key Findings

1. **Agent Provisioning**: Uses `GET /pipelines/{id}/agents/add` with query parameters
2. **Agent Assignment**: Uses `PUT /pipelines/{id}/agents/{agent_id}`
3. **Credentials**: Configured separately via `/config/credentials`
4. **Entity Creation**: Three-step process (create-table statement, entity config, columns mapping)
5. **Agent User Tags**: Automatically generated (e.g., `ship-cleanly-ibm-iseries`)

## Agent IDs
- **Source (ibm-iseries)**: `00c7ac81`
- **Target (mssql-cdc)**: `92de6be5`

## New Findings (Updated Pipeline: 8aeb9fb6)

### Additional Pipeline Created
- **Pipeline ID**: `8aeb9fb6`
- **Pipeline Name**: `Test-CLI-Pipeline`
- **Source Agent**: `dcc35915` (ibm-iseries)
- **Target Agent**: `be2d59bd` (mssql-cdc)
- **Entity**: `GSLIBTST.CUSTOMERS` → `dbo.CUSTOMERS`
- **Entity ID**: `98fd97b8`

### New API Endpoints Discovered

#### Runtime / Sync APIs
```http
# One-time snapshot (truncate + insert)
POST /pipelines/{pipeline_id}/commands/sync/one-time-snapshot?entity={entity_id}&snapshotWriteMethod=INSERT

# CDC with reset checkpoint
POST /pipelines/{pipeline_id}/commands/sync/redo?entity={entity_id}&snapshotWriteMethod=UPSERT

# Stop entity
POST /pipelines/{pipeline_id}/commands/sync/stop?entity={entity_id}&groupId=_default
```

#### Discovery APIs
```http
# Get node info
GET /pipelines/{pipeline_id}/agents/{agent_id}/discovery/node-info

# List schemas
GET /pipelines/{pipeline_id}/agents/{agent_id}/discovery/schemas

# List tables in schema
GET /pipelines/{pipeline_id}/agents/{agent_id}/discovery/tables?schema={schema_name}

# List columns in table
GET /pipelines/{pipeline_id}/agents/{agent_id}/discovery/columns?tableschema={schema}&tablename={table}
```

#### Additional Pipeline APIs
```http
# Get pipeline config groups
GET /pipelines/{pipeline_id}/config/groups

# Update pipeline (name/description)
PUT /pipelines/{pipeline_id}
```

### Sync API Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `snapshotWriteMethod` | `INSERT`, `UPSERT` | How to write data to target |
| `entity` | Entity ID | Which entity to sync |
| `groupId` | `_default` | Entity group (usually _default) |

### Key Differences from Original Capture

1. **Snapshot vs CDC**: Different endpoints for one-time snapshot vs continuous CDC
2. **Write Methods**: INSERT (truncate first) vs UPSERT (merge/insert)
3. **Entity ID**: Required for runtime operations (different from entity name)
4. **Group ID**: Entities are organized in groups (default: `_default`)


## CLI Implementation Status

### Implemented ✓
- Authentication (`/authentication/login`)
- Pipeline CRUD (`/pipelines`, `/pipelines/{id}`)
- Agent provisioning (`/agents/add`, `/agents/{id}`)
- Agent configuration (`/config/credentials`, `/config/specific`)
- Discovery (`/discovery/schemas`, `/discovery/tables`, `/discovery/columns`)
- Entity creation (`/config/entities`)
- CDC start/stop (`/commands/sync/redo`, `/commands/sync/stop`)

### Needs Update ⚠️
- **One-time snapshot**: CLI uses old `withSnapshot` parameter, should use `/commands/sync/one-time-snapshot` endpoint
- **Entity ID tracking**: CLI should capture and store entity IDs (not just names) for runtime operations
- **Discovery node-info**: Not implemented (`/discovery/node-info`)

### Recommended CLI Updates

```python
# Add to GlueSyncClient class:
def start_entity_snapshot(self, pipeline_id: str, entity_id: str, 
                           snapshot_method: str = "INSERT") -> bool:
    """Start one-time snapshot"""
    params = {
        "entity": entity_id,
        "snapshotWriteMethod": snapshot_method
    }
    resp = self.request("POST", 
        f"/pipelines/{pipeline_id}/commands/sync/one-time-snapshot", 
        params=params)
    return resp.status_code == 202

# Update entity start command to support modes:
# --mode snapshot (uses one-time-snapshot)
# --mode cdc (uses redo)
# --mode both (snapshot then cdc)
```


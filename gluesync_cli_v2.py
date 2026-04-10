#\!/usr/bin/env python3
"""GlueSync CLI v2 - kubectl-style"""

import argparse
import json
import os
import sys
import urllib3
urllib3.disable_warnings()

try:
    import requests
except ImportError:
    print("Error: pip3 install requests")
    sys.exit(1)


class GlueSyncClient:
    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = False):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = verify_ssl
        resp = self.session.post(f"{base_url}/authentication/login",
                                 json={"username": username, "password": password})
        if resp.status_code != 200:
            raise Exception(f"Auth failed: {resp.text}")
        self.token = resp.json()["apiToken"]
    
    def request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        return self.session.request(method, url, headers=headers, **kwargs)
    
    def list_pipelines(self):
        resp = self.request("GET", "/pipelines")
        return resp.json() if resp.status_code == 200 else []
    
    def get_pipeline(self, pipeline_id: str):
        resp = self.request("GET", f"/pipelines/{pipeline_id}")
        return resp.json() if resp.status_code == 200 else None
    
    def list_entities(self, pipeline_id: str):
        resp = self.request("GET", f"/pipelines/{pipeline_id}/entities")
        if resp.status_code != 200:
            return []
        return [e.get('entity', {}) for e in resp.json()]
    
    def list_agents(self, pipeline_id: str):
        """List agents for a pipeline"""
        resp = self.request("GET", f"/pipelines/{pipeline_id}/agents")
        return resp.json() if resp.status_code == 200 else []
    
    def get_agent_discovery_schemas(self, pipeline_id: str, agent_id: str):
        """Discover available schemas from an agent"""
        resp = self.request("GET", f"/pipelines/{pipeline_id}/agents/{agent_id}/discovery/schemas")
        return resp.json() if resp.status_code == 200 else []
    
    def enter_maintenance_mode(self, pipeline_id: str):
        """Put pipeline into maintenance mode"""
        resp = self.request("POST", f"/pipelines/{pipeline_id}/commands/maintenance/enter")
        return resp.status_code == 202
    
    def exit_maintenance_mode(self, pipeline_id: str):
        """Exit maintenance mode (resume operations)"""
        resp = self.request("POST", f"/pipelines/{pipeline_id}/commands/maintenance/exit")
        return resp.status_code == 202
    
    def _map_db_type(self, source_type: str) -> str:
        """Map AS400/DB2 data types to MSSQL data types"""
        type_mapping = {
            'INTEGER': 'int',
            'SMALLINT': 'smallint',
            'BIGINT': 'bigint',
            'DECIMAL': 'decimal',
            'NUMERIC': 'decimal',
            'CHARACTER': 'varchar',
            'CHAR': 'varchar',
            'CHARACTER VARYING': 'varchar',
            'VARCHAR': 'varchar',
            'DATE': 'date',
            'TIME': 'time',
            'TIMESTAMP': 'datetime',
            'FLOAT': 'float',
            'REAL': 'real',
            'DOUBLE': 'float',
            'BLOB': 'varbinary',
            'CLOB': 'varchar',
        }
        return type_mapping.get(source_type.upper(), 'varchar')
    
    def get_entity(self, pipeline_id: str, entity_id: str):
        entities = self.list_entities(pipeline_id)
        for e in entities:
            if e.get('entityId') == entity_id:
                return e
        return None
    
    def delete_pipeline(self, pipeline_id: str):
        """Delete a pipeline"""
        resp = self.request("DELETE", f"/pipelines/{pipeline_id}")
        return resp.status_code == 200
    
    def create_pipeline(self, name: str, description: str = "", 
                       source_type: str = "AS400", target_type: str = "MSSQL",
                       source_host: str = "", source_user: str = "", source_password: str = "",
                       target_host: str = "", target_user: str = "", target_password: str = "",
                       target_database: str = ""):
        """Create a new pipeline with source and target agents"""
        pipeline_data = {
            "name": name,
            "description": description
        }
        
        # Create pipeline first
        resp = self.request("POST", "/pipelines", json=pipeline_data)
        if resp.status_code != 200:
            raise Exception(f"Failed to create pipeline: {resp.text}")
        
        response_data = resp.json()
        # Try different possible ID field names
        pipeline_id = response_data.get("id") or response_data.get("pipelineId") or response_data.get("_id")
        
        if not pipeline_id:
            # If no ID in response, list pipelines to find the new one
            pipelines = self.list_pipelines()
            for p in pipelines:
                if p.get("name") == name:
                    pipeline_id = p.get("id")
                    break
        
        # TODO: Add agent configuration (need API endpoint from MITM capture)
        # This will be updated once we capture the agent creation API
        
        return pipeline_id
    
    def create_target_table(self, pipeline_id: str, schema: str, table_name: str, 
                           columns: list, primary_key: str = None, warn_identity_pk: bool = True):
        """Create a target table via GlueSync (generates SQL CREATE TABLE)
        
        Args:
            pipeline_id: Pipeline ID
            schema: Target schema name
            table_name: Target table name
            columns: List of column definitions
            primary_key: Primary key column name
            warn_identity_pk: If True, warn about IDENTITY/AUTO_INCREMENT PK columns
        """
        # Build CREATE TABLE statement
        column_defs = []
        pk_columns = []
        
        for col in columns:
            col_name = col.get('name')
            col_type = col.get('type', 'VARCHAR(100)')
            nullable = col.get('nullable', True)
            is_identity = col.get('is_identity', False) or col.get('auto_increment', False)
            
            # Check for IDENTITY/AUTO_INCREMENT on primary key
            if warn_identity_pk and is_identity:
                is_pk = primary_key and col_name == primary_key
                if is_pk:
                    print(f"⚠️  WARNING: Column '{col_name}' is IDENTITY/AUTO_INCREMENT and is used as PRIMARY KEY", file=sys.stderr)
                    print(f"   In replication, PK values come from the source system.", file=sys.stderr)
                    print(f"   The target should NOT auto-generate PK values!", file=sys.stderr)
                    print(f"   Consider removing IDENTITY property or use a different column.", file=sys.stderr)
                    user_input = input("   Continue anyway? (yes/no): ")
                    if user_input.lower() != 'yes':
                        raise Exception("Aborted: Remove IDENTITY from PK column or confirm to continue")
            
            col_def = f"   [{col_name}] {col_type}"
            if not nullable:
                col_def += " NOT NULL"
            column_defs.append(col_def)
            
            # Track PK columns
            if primary_key and col_name == primary_key:
                pk_columns.append(col_name)
        
        # Add primary key constraint if specified
        if pk_columns:
            column_defs.append(f"   PRIMARY KEY (\n      {', '.join('[' + c + ']' for c in pk_columns)}\n   )")
        
        newline = '\n'
        create_sql = f"CREATE TABLE [{schema}].[{table_name}] (\n{newline.join(column_defs)}\n)"
        
        # Send to GlueSync for execution
        payload = {
            "statement": create_sql
        }
        
        resp = self.request("PUT", 
                           f"/pipelines/{pipeline_id}/config/entities/statements/create-table",
                           json=payload)
        if resp.status_code != 200:
            raise Exception(f"Failed to create table: {resp.text}")
        
        return resp.json()

    def create_entity(self, pipeline_id: str, source_library: str, source_table: str,
                     target_schema: str, target_table: str, polling_interval: int = 500,
                     batch_size: int = 1000, skip_rrn: bool = True,
                     source_columns: list = None, source_keys: list = None):
        """Create a new entity for table replication
        
        Args:
            pipeline_id: Pipeline ID
            source_library: Source AS400 library
            source_table: Source table name
            target_schema: Target MSSQL schema
            target_table: Target table name
            polling_interval: Polling interval in milliseconds
            batch_size: Batch size for data fetching
            skip_rrn: If True, exclude AS400 _RRN metadata field from target mapping
            source_columns: Optional list of source columns (auto-discovered if not provided)
            source_keys: Optional list of source keys (auto-discovered if not provided)
        """
        # First, get pipeline to find agent IDs
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            raise Exception(f"Pipeline {pipeline_id} not found")
        
        # Get agent IDs from pipeline
        agents = pipeline.get('agents', [])
        source_agent_id = None
        target_agent_id = None
        
        for agent in agents:
            if agent.get('agentType') == 'SOURCE':
                source_agent_id = agent.get('agentId')
            elif agent.get('agentType') == 'TARGET':
                target_agent_id = agent.get('agentId')
        
        if not source_agent_id or not target_agent_id:
            raise Exception("Source and target agents must be configured before creating entities")
        
        # Auto-discover schema from source if not provided
        if source_columns is None or source_keys is None:
            print(f"Discovering schema for {source_library}.{source_table}...", file=sys.stderr)
            schemas = self.get_agent_discovery_schemas(pipeline_id, source_agent_id)
            
            # Find the table schema
            source_columns = []
            source_keys = []
            schema_found = False
            
            for schema in schemas:
                if schema.get('schema') == source_library:
                    for table in schema.get('tables', []):
                        if table.get('name') == source_table:
                            source_columns = table.get('columns', [])
                            source_keys = table.get('keys', [])
                            schema_found = True
                            print(f"✓ Found {len(source_columns)} columns and {len(source_keys)} keys", file=sys.stderr)
                            break
                if schema_found:
                    break
            
            if not schema_found:
                raise Exception(f"Table {source_library}.{source_table} not found in schema discovery")
        
        # Build target columns (map from source columns)
        target_columns = []
        for col in source_columns:
            # Skip _RRN if requested
            if skip_rrn and col.get('name', '').startswith('_RRN'):
                print(f"Skipping AS400 _RRN field", file=sys.stderr)
                continue
            
            # Map source type to target type
            source_type = col.get('type', 'VARCHAR')
            target_type = self._map_db_type(source_type)
            
            target_columns.append({
                "id": col.get('id', 0),
                "name": col.get('name'),
                "type": target_type
            })
        
        # Build target keys (same as source keys, skipping _RRN)
        target_keys = []
        for key in source_keys:
            if skip_rrn and key.get('name', '').startswith('_RRN'):
                continue
            target_keys.append({
                "id": key.get('id', 0),
                "name": key.get('name'),
                "type": self._map_db_type(key.get('type', 'VARCHAR'))
            })
        
        # Build columns mapping matrix
        columns_mapping_matrix = []
        for src_col in source_columns:
            # Skip _RRN
            if skip_rrn and src_col.get('name', '').startswith('_RRN'):
                continue
            
            # Find corresponding target column
            for tgt_col in target_columns:
                if tgt_col.get('name') == src_col.get('name'):
                    columns_mapping_matrix.append({
                        "sourceTableObjectId": 0,  # Will be set by server
                        "targetTableObjectId": 0,  # Will be set by server
                        "sourceColumnId": src_col.get('id', 0),
                        "targetColumnId": tgt_col.get('id', 0)
                    })
                    break
        
        print(f"Built {len(columns_mapping_matrix)} column mappings", file=sys.stderr)
        
        # Build entity payload based on captured API structure
        entity_data = {
            "entities": [
                {
                    "entityId": "",
                    "entityName": f"{source_library}.{source_table}",
                    "agentEntities": [
                        {
                            "type": "SingleTable",
                            "entityId": "",
                            "entityName": f"{source_library}.{source_table}",
                            "agentEntityId": "",
                            "entityType": {
                                "type": "Source",
                                "maxFetchItemsCountPerIteration": batch_size,
                                "maxTransactionMessageKbSize": 1024,
                                "pollingIntervalMilliseconds": polling_interval,
                                "unchangedDataFilterType": "ENTIRE_ROW"
                            },
                            "agentId": source_agent_id,
                            "orderIndex": 0,
                            "customProperties": {
                                "useDedicatedJournalReader": False
                            },
                            "tablesProperties": {
                                f"{source_library}.{source_table}": {}
                            },
                            "table": {
                                "id": 0,
                                "schema": source_library,
                                "name": source_table
                            },
                            "columns": source_columns,  # ✅ NOW POPULATED
                            "keys": source_keys          # ✅ NOW POPULATED
                        },
                        {
                            "type": "SingleTable",
                            "entityId": "",
                            "entityName": f"{source_library}.{source_table}",
                            "agentEntityId": "",
                            "entityType": {
                                "type": "Target",
                                "allowedOperations": ["INSERT", "UPDATE", "DELETE", "TRUNCATE"],
                                "snapshotWritingConcurrency": 2,
                                "columnsMappingMatrix": columns_mapping_matrix,  # ✅ NOW POPULATED
                                "tablesWithUnlockedSchema": [],
                                "tablesWithUnlockedDataTypes": [],
                                "useBulkOperationsDuringCDC": False,
                                "useBulkOperationsWhileSnapshot": False
                            },
                            "agentId": target_agent_id,
                            "orderIndex": 0,
                            "customProperties": {
                                "maxWriteBatchSize": batch_size,
                                "maxDeleteBatchSize": batch_size,
                                "maxWriteBulkSize": 250000,
                                "preSnapshotCommand": "",
                                "postSnapshotCommand": ""
                            },
                            "tablesProperties": {
                                f"{source_library}.{source_table}": {}
                            },
                            "table": {
                                "id": 0,
                                "schema": target_schema,
                                "name": target_table
                            },
                            "columns": target_columns,  # ✅ NOW POPULATED
                            "keys": target_keys          # ✅ NOW POPULATED
                        }
                    ],
                    "groupId": "_default",
                    "orderIndex": 0
                }
            ]
        }
        
        # Create entity via API
        resp = self.request("PUT", f"/pipelines/{pipeline_id}/config/entities", json=entity_data)
        if resp.status_code != 200:
            raise Exception(f"Failed to create entity: {resp.text}")
        
        # Return the entity configuration
        return resp.json()
    
    def delete_entity(self, pipeline_id: str, entity_id: str):
        """Delete an entity from the pipeline
        
        Args:
            pipeline_id: Pipeline ID
            entity_id: Entity ID to delete
            
        Returns:
            True if deletion successful
        """
        resp = self.request("DELETE", f"/pipelines/{pipeline_id}/entities/{entity_id}")
        return resp.status_code in [200, 202, 204]
    
    def start_entity(self, pipeline_id: str, entity_id: str, mode: str = "snapshot"):
        """Start entity replication (snapshot or CDC)"""
        # TODO: Implementation pending MITM API capture
        raise NotImplementedError("Entity start API endpoint needed")
    
    def stop_entity(self, pipeline_id: str, entity_id: str):
        """Stop entity replication"""
        # TODO: Implementation pending MITM API capture
        raise NotImplementedError("Entity stop API endpoint needed")


def format_table(data, columns):
    if not data:
        return "No data found."
    col_widths = {col: max(len(col), max(len(str(row.get(col, ""))) for row in data)) for col in columns}
    lines = [" | ".join(col.upper().ljust(col_widths[col]) for col in columns)]
    lines.append("-" * len(lines[0]))
    for row in data:
        lines.append(" | ".join(str(row.get(col, "")).ljust(col_widths[col]) for col in columns))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="GlueSync CLI v2")
    parser.add_argument("--output", "-o", choices=["table", "json"], default="table")
    subparsers = parser.add_subparsers(dest="action", help="Action")
    
    # GET
    get_parser = subparsers.add_parser("get", help="Get resources")
    get_sub = get_parser.add_subparsers(dest="resource")
    get_sub.add_parser("pipelines", help="List pipelines")
    p1 = get_sub.add_parser("pipeline", help="Get pipeline")
    p1.add_argument("id")
    p2 = get_sub.add_parser("entities", help="List entities")
    p2.add_argument("--pipeline", "-p", required=True)
    p3 = get_sub.add_parser("entity", help="Get entity")
    p3.add_argument("id")
    p3.add_argument("--pipeline", "-p", required=True)
    p3.add_argument("--full", "-f", action="store_true", help="Show full details including columns and mappings")
    
    # MAINTENANCE
    maint_parser = subparsers.add_parser("maintenance", help="Pipeline maintenance mode")
    maint_sub = maint_parser.add_subparsers(dest="mode")
    maint_enter = maint_sub.add_parser("enter", help="Enter maintenance mode")
    maint_enter.add_argument("pipeline_id")
    maint_exit = maint_sub.add_parser("exit", help="Exit maintenance mode (resume)")
    maint_exit.add_argument("pipeline_id")
    
    # AGENTS
    agents_parser = subparsers.add_parser("agents", help="List pipeline agents")
    agents_parser.add_argument("pipeline_id")
    
    # SCHEMA DISCOVERY
    schema_parser = subparsers.add_parser("discover-schema", help="Discover table schema from source")
    schema_parser.add_argument("pipeline_id")
    schema_parser.add_argument("--agent-id", required=True, help="Source agent ID")
    schema_parser.add_argument("--library", required=True)
    schema_parser.add_argument("--table", required=True)
    
    # CREATE
    create_parser = subparsers.add_parser("create", help="Create resources")
    create_sub = create_parser.add_subparsers(dest="resource")
    
    # Create pipeline
    cp = create_sub.add_parser("pipeline", help="Create pipeline")
    cp.add_argument("--name", "-n", required=True)
    cp.add_argument("--description", "-d", default="")
    cp.add_argument("--source-type", default="AS400")
    cp.add_argument("--target-type", default="MSSQL")
    cp.add_argument("--source-host", default="")
    cp.add_argument("--source-user", default="")
    cp.add_argument("--source-password", default="")
    cp.add_argument("--target-host", default="")
    cp.add_argument("--target-user", default="")
    cp.add_argument("--target-password", default="")
    cp.add_argument("--target-database", default="")
    
    # Create entity
    ce = create_sub.add_parser("entity", help="Create entity")
    ce.add_argument("--pipeline", "-p", required=True)
    ce.add_argument("--source-library", required=True)
    ce.add_argument("--source-table", required=True)
    ce.add_argument("--target-schema", required=True)
    ce.add_argument("--target-table", required=True)
    ce.add_argument("--polling-interval", type=int, default=500)
    ce.add_argument("--batch-size", type=int, default=1000)
    ce.add_argument("--skip-rrn", action="store_true", default=True, 
                   help="Skip AS400 _RRN metadata field from target mapping (default: True)")
    ce.add_argument("--include-rrn", action="store_false", dest="skip_rrn",
                   help="Include AS400 _RRN metadata field in target mapping")
    
    # DELETE
    delete_parser = subparsers.add_parser("delete", help="Delete resources")
    delete_sub = delete_parser.add_subparsers(dest="resource")
    
    # Delete pipeline
    dp = delete_sub.add_parser("pipeline", help="Delete pipeline")
    dp.add_argument("id")
    
    # Delete entity
    de = delete_sub.add_parser("entity", help="Delete entity")
    de.add_argument("id")
    de.add_argument("--pipeline", "-p", required=True)
    
    # START/STOP
    start_parser = subparsers.add_parser("start", help="Start entity replication")
    start_parser.add_argument("entity_id")
    start_parser.add_argument("--pipeline", "-p", required=True)
    start_parser.add_argument("--mode", choices=["snapshot", "cdc"], default="snapshot")
    
    stop_parser = subparsers.add_parser("stop", help="Stop entity replication")
    stop_parser.add_argument("entity_id")
    stop_parser.add_argument("--pipeline", "-p", required=True)
    
    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        sys.exit(1)
    
    # Connect
    password = os.getenv("GLUESYNC_ADMIN_PASSWORD") or os.getenv("ADMIN_PASS")
    if not password:
        print("Error: GLUESYNC_ADMIN_PASSWORD environment variable not set", file=sys.stderr)
        print("Please set it or add to .env file", file=sys.stderr)
        sys.exit(1)
    client = GlueSyncClient("https://localhost:1717", "admin", password)
    
    # Handle commands
    if args.action == "maintenance":
        if args.mode == "enter":
            success = client.enter_maintenance_mode(args.pipeline_id)
            if success:
                print(f"✓ Pipeline {args.pipeline_id} entered maintenance mode")
            else:
                print(f"✗ Failed to enter maintenance mode", file=sys.stderr)
                sys.exit(1)
        elif args.mode == "exit":
            success = client.exit_maintenance_mode(args.pipeline_id)
            if success:
                print(f"✓ Pipeline {args.pipeline_id} resumed from maintenance mode")
            else:
                print(f"✗ Failed to exit maintenance mode", file=sys.stderr)
                sys.exit(1)
    
    elif args.action == "agents":
        agents = client.list_agents(args.pipeline_id)
        if agents:
            print(f"Agents for pipeline {args.pipeline_id}:")
            for agent in agents:
                print(f"  - {agent.get('agentId')}: {agent.get('agentType')}")
        else:
            print("No agents found")
    
    elif args.action == "discover-schema":
        print(f"Discovering schema for {args.library}.{args.table}...", file=sys.stderr)
        schemas = client.get_agent_discovery_schemas(args.pipeline_id, args.agent_id)
        # Find the specific table schema
        found = False
        for schema in schemas:
            if schema.get('schema') == args.library:
                for table in schema.get('tables', []):
                    if table.get('name') == args.table:
                        print(json.dumps(table, indent=2))
                        found = True
                        break
        if not found:
            print(f"Table {args.library}.{args.table} not found", file=sys.stderr)
            sys.exit(1)
    
    elif args.action == "get":
        if args.resource == "pipelines":
            data = client.list_pipelines()
            print(format_table(data, ["id", "name", "configurationCompleted"]) if args.output == "table" else json.dumps(data, indent=2))
        elif args.resource == "pipeline":
            data = client.get_pipeline(args.id)
            print(json.dumps(data, indent=2) if data else "Not found")
        elif args.resource == "entities":
            data = client.list_entities(args.pipeline)
            print(format_table(data, ["entityId", "entityName"]) if args.output == "table" else json.dumps(data, indent=2))
        elif args.resource == "entity":
            data = client.get_entity(args.pipeline, args.id)
            if not data:
                print("Not found")
                sys.exit(1)
            if args.output == "json":
                print(json.dumps(data, indent=2))
            else:
                # Format entity summary
                print(f"=== Entity Summary ===")
                print(f"Entity ID:   {data.get('entityId')}")
                print(f"Name:        {data.get('entityName')}")
                print(f"Group:       {data.get('groupId', '_default')}")
                print()
                
                for ae in data.get('agentEntities', []):
                    et = ae.get('entityType', {})
                    agent_type = et.get('type', 'Unknown')
                    print(f"=== {agent_type} Agent: {ae.get('agentId')} ===")
                    
                    table = ae.get('table', {})
                    print(f"  Table:     {table.get('schema', 'N/A')}.{table.get('name', 'N/A')}")
                    
                    if agent_type == 'Source':
                        print(f"  Polling:   {et.get('pollingIntervalMilliseconds', 'N/A')}ms")
                        print(f"  Batch:     {et.get('maxFetchItemsCountPerIteration', 'N/A')} rows")
                    elif agent_type == 'Target':
                        write_method = et.get('snapshotWriteMethod', 'NOT SET (default: MERGE)')
                        print(f"  Write:     {write_method}")
                        print(f"  Ops:       {', '.join(et.get('allowedOperations', []))}")
                        print(f"  Concurrency: {et.get('snapshotWritingConcurrency', 'N/A')}")
                    
                    # Keys
                    keys = ae.get('keys', [])
                    if keys:
                        print(f"  Keys:      {', '.join(k.get('name', 'N/A') for k in keys)}")
                    
                    # Full details: columns
                    if args.full:
                        columns = ae.get('columns', [])
                        if columns:
                            print(f"\n  Columns:")
                            for col in columns:
                                print(f"    - {col.get('name')} ({col.get('type')})")
                        
                        # Column mappings for target
                        if agent_type == 'Target':
                            mappings = et.get('columnsMappingMatrix', [])
                            if mappings:
                                print(f"\n  Column Mappings:")
                                for m in mappings[:5]:  # Show first 5
                                    print(f"    Source ID {m.get('sourceColumnId')} -> Target ID {m.get('targetColumnId')}")
                                if len(mappings) > 5:
                                    print(f"    ... and {len(mappings) - 5} more")
                    print()
    
    elif args.action == "create":
        if args.resource == "pipeline":
            try:
                pipeline_id = client.create_pipeline(
                    name=args.name,
                    description=args.description,
                    source_type=args.source_type,
                    target_type=args.target_type,
                    source_host=args.source_host,
                    source_user=args.source_user,
                    source_password=args.source_password,
                    target_host=args.target_host,
                    target_user=args.target_user,
                    target_password=args.target_password,
                    target_database=args.target_database
                )
                print(f"✓ Pipeline created: {pipeline_id}")
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        elif args.resource == "entity":
            try:
                result = client.create_entity(
                    pipeline_id=args.pipeline,
                    source_library=args.source_library,
                    source_table=args.source_table,
                    target_schema=args.target_schema,
                    target_table=args.target_table,
                    polling_interval=args.polling_interval,
                    batch_size=args.batch_size,
                    skip_rrn=args.skip_rrn
                )
                entity_name = result.get('entities', [{}])[0].get('entityName', 'Unknown')
                print(f"✓ Entity created: {entity_name}")
            except NotImplementedError as e:
                print(f"⚠ {e}", file=sys.stderr)
                print("Please capture the API via MITM proxy and retry", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
    
    elif args.action == "delete":
        if args.resource == "pipeline":
            if client.delete_pipeline(args.id):
                print(f"✓ Pipeline deleted: {args.id}")
            else:
                print(f"Error: Failed to delete pipeline {args.id}", file=sys.stderr)
                sys.exit(1)
        elif args.resource == "entity":
            try:
                client.delete_entity(args.pipeline, args.id)
                print(f"✓ Entity deleted: {args.id}")
            except NotImplementedError as e:
                print(f"⚠ {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
    
    elif args.action == "start":
        try:
            client.start_entity(args.pipeline, args.entity_id, mode=args.mode)
            print(f"✓ Entity {args.entity_id} started in {args.mode} mode")
        except NotImplementedError as e:
            print(f"⚠ {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.action == "stop":
        try:
            client.stop_entity(args.pipeline, args.entity_id)
            print(f"✓ Entity {args.entity_id} stopped")
        except NotImplementedError as e:
            print(f"⚠ {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

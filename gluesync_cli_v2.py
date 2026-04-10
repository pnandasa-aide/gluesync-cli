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
                           columns: list, primary_key: str = None):
        """Create a target table via GlueSync (generates SQL CREATE TABLE)"""
        # Build CREATE TABLE statement
        column_defs = []
        for col in columns:
            col_name = col.get('name')
            col_type = col.get('type', 'VARCHAR(100)')
            nullable = col.get('nullable', True)
            
            col_def = f"   [{col_name}] {col_type}"
            if not nullable:
                col_def += " NOT NULL"
            column_defs.append(col_def)
        
        # Add primary key if specified
        if primary_key:
            column_defs.append(f"   PRIMARY KEY (\n      [{primary_key}]\n   )")
        
        create_sql = f"CREATE TABLE [{schema}].[{table_name}] (\n{',\\n'.join(column_defs)}\n)"
        
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
                     batch_size: int = 1000):
        """Create a new entity for table replication"""
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
                                "id": 0,  # Will be auto-assigned by server
                                "schema": source_library,
                                "name": source_table
                            },
                            "columns": [],  # Will be auto-populated by server
                            "keys": []
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
                                "columnsMappingMatrix": [],  # Will be auto-populated
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
                            "columns": [],
                            "keys": []
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
        """Delete an entity"""
        # TODO: Implementation pending MITM API capture
        raise NotImplementedError("Entity deletion API endpoint needed")
    
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
    if args.action == "get":
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
                    batch_size=args.batch_size
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

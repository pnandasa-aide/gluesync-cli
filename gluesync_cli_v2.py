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


if __name__ == "__main__":
    main()

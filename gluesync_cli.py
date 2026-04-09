#!/usr/bin/env python3
"""
GlueSync CLI - Command Line Interface for Pipeline Management

Usage:
    gluesync-cli [global-options] <command> [subcommand] [options]

Examples:
    gluesync-cli pipeline list
    gluesync-cli pipeline create --name "My Pipeline" --interactive
    gluesync-cli agent list <pipeline-id>
    gluesync-cli entity start <pipeline-id> --entity <entity-id> --with-snapshot
    gluesync-cli runtime status <pipeline-id> --watch
"""

import argparse
import json
import os
import sys
import time
import urllib3
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip3 install requests")
    sys.exit(1)


@dataclass
class Config:
    """Configuration class"""
    base_url: str
    verify_ssl: bool
    username: str
    password: str
    output_format: str = "table"


class GlueSyncClient:
    """API Client for GlueSync Core Hub"""
    
    def __init__(self, config: Config):
        self.config = config
        self.token = None
        self.session = requests.Session()
        self.session.verify = config.verify_ssl
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate and get API token"""
        resp = self.session.post(
            f"{self.config.base_url}/authentication/login",
            json={"username": self.config.username, "password": self.config.password}
        )
        if resp.status_code != 200:
            raise Exception(f"Authentication failed: {resp.text}")
        self.token = resp.json()["apiToken"]
    
    def _headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make authenticated request"""
        url = f"{self.config.base_url}{path}"
        headers = self._headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        return self.session.request(method, url, headers=headers, **kwargs)
    
    # Pipeline Operations
    def list_pipelines(self) -> List[Dict]:
        resp = self.request("GET", "/pipelines")
        return resp.json() if resp.status_code == 200 else []
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Dict]:
        resp = self.request("GET", f"/pipelines/{pipeline_id}")
        return resp.json() if resp.status_code == 200 else None
    
    def create_pipeline(self, name: str, description: str = "") -> Optional[str]:
        resp = self.request("POST", "/pipelines", json={
            "name": name,
            "description": description,
            "enabled": True
        })
        if resp.status_code == 200:
            return resp.json().get("pipelineId")
        return None
    
    def update_pipeline(self, pipeline_id: str, name: str = None, description: str = None) -> bool:
        data = {}
        if name:
            data["name"] = name
        if description:
            data["description"] = description
        resp = self.request("PUT", f"/pipelines/{pipeline_id}", json=data)
        return resp.status_code == 200
    
    def delete_pipeline(self, pipeline_id: str) -> bool:
        resp = self.request("DELETE", f"/pipelines/{pipeline_id}")
        return resp.status_code == 200
    
    # Agent Operations
    def list_agents(self, pipeline_id: str) -> List[Dict]:
        resp = self.request("GET", f"/pipelines/{pipeline_id}/agents")
        return resp.json() if resp.status_code == 200 else []
    
    def provision_agent(self, pipeline_id: str, agent_type: str, 
                        internal_name: str, user_tag: str) -> Optional[str]:
        """Provision a new agent"""
        params = {
            "agentType": agent_type,
            "agentInternalName": internal_name,
            "agentUserTag": user_tag
        }
        resp = self.request("GET", f"/pipelines/{pipeline_id}/agents/add", params=params)
        if resp.status_code == 200:
            return resp.json().get("agentId")
        return None
    
    def assign_agent(self, pipeline_id: str, agent_id: str, agent_role: str) -> bool:
        """Assign agent to pipeline"""
        params = {"agentType": agent_role.upper()}
        resp = self.request("PUT", f"/pipelines/{pipeline_id}/agents/{agent_id}", params=params)
        return resp.status_code == 200
    
    def configure_agent_credentials(self, pipeline_id: str, agent_id: str, 
                                     host: str, username: str, password: str,
                                     database: str = "", port: int = 0,
                                     trust_cert: bool = False) -> bool:
        """Configure agent credentials"""
        data = {
            "hostCredentials": {
                "connectionName": "",
                "host": host,
                "port": port,
                "databaseName": database,
                "username": username,
                "password": password,
                "disableAuth": False,
                "enableTls": False,
                "trustServerCertificate": trust_cert,
                "useUploadedTrustStore": False,
                "useUploadedKeyStore": False,
                "useUploadedCertificate": False,
                "additionalHosts": [{"host": ""}],
                "minConnectionsCount": 5,
                "maxConnectionsCount": 25
            }
        }
        resp = self.request("PUT", f"/pipelines/{pipeline_id}/agents/{agent_id}/config/credentials", json=data)
        return resp.status_code == 202
    
    def configure_agent_specific(self, pipeline_id: str, agent_id: str) -> bool:
        """Configure agent-specific settings"""
        data = {"configuration": {}}
        resp = self.request("PUT", f"/pipelines/{pipeline_id}/agents/{agent_id}/config/specific", json=data)
        return resp.status_code == 202
    
    # Entity Operations
    def list_entities(self, pipeline_id: str) -> List[Dict]:
        resp = self.request("GET", f"/pipelines/{pipeline_id}/entities")
        return resp.json() if resp.status_code == 200 else []
    
    def create_entity(self, pipeline_id: str, entity_config: Dict) -> bool:
        """Create entity with full configuration"""
        resp = self.request("PUT", f"/pipelines/{pipeline_id}/config/entities", json=entity_config)
        return resp.status_code == 200
    
    def update_entity_write_method(self, pipeline_id: str, entity_id: str, write_method: str) -> bool:
        """Update entity write method (MERGE, UPSERT, INSERT)"""
        # Get current entity config
        entities = self.list_entities(pipeline_id)
        entity_config = None
        for e in entities:
            if e.get('entity', {}).get('entityId') == entity_id:
                entity_config = e['entity']
                break
        
        if not entity_config:
            return False
        
        # Update target agent write method
        for ae in entity_config.get('agentEntities', []):
            if ae.get('entityType', {}).get('type') == 'Target':
                ae['entityType']['snapshotWriteMethod'] = write_method
        
        resp = self.request("PUT", f"/pipelines/{pipeline_id}/config/entities", 
                          json={"entities": [entity_config]})
        return resp.status_code == 200
    
    # Runtime Operations
    def start_entity(self, pipeline_id: str, entity_id: str, 
                     with_snapshot: bool = True, snapshot_method: str = "UPSERT") -> bool:
        """Start entity processing"""
        params = {
            "entity": entity_id,
            "withSnapshot": str(with_snapshot).lower(),
            "snapshotWriteMethod": snapshot_method
        }
        resp = self.request("POST", f"/pipelines/{pipeline_id}/commands/sync/redo", params=params)
        return resp.status_code == 202
    
    def stop_entity(self, pipeline_id: str, entity_id: str, group_id: str = "_default") -> bool:
        """Stop entity processing"""
        params = {
            "entity": entity_id,
            "groupId": group_id
        }
        resp = self.request("POST", f"/pipelines/{pipeline_id}/commands/sync/stop", params=params)
        return resp.status_code == 202
    
    # Discovery Operations
    def discovery_schemas(self, pipeline_id: str, agent_id: str) -> List[str]:
        resp = self.request("GET", f"/pipelines/{pipeline_id}/agents/{agent_id}/discovery/schemas")
        return resp.json() if resp.status_code == 200 else []
    
    def get_available_agents(self) -> List[Dict]:
        """Get list of available agent types from Core Hub"""
        # This endpoint may vary - trying common patterns
        resp = self.request("GET", "/agents/types")
        if resp.status_code == 200:
            return resp.json()
        # Fallback: return known agent types from documentation
        return [
            {"name": "IBM iSeries (AS400)", "internalName": "ibm-iseries", "type": "source"},
            {"name": "Microsoft SQL Server (CDC)", "internalName": "mssql-cdc", "type": "target"},
            {"name": "Oracle", "internalName": "oracle", "type": "both"},
            {"name": "PostgreSQL", "internalName": "postgresql", "type": "both"},
            {"name": "MySQL", "internalName": "mysql", "type": "both"},
            {"name": "MongoDB", "internalName": "mongodb", "type": "both"},
        ]
    
    def discovery_tables(self, pipeline_id: str, agent_id: str, schema: str) -> List[str]:
        params = {"schema": schema}
        resp = self.request("GET", f"/pipelines/{pipeline_id}/agents/{agent_id}/discovery/tables", params=params)
        return resp.json() if resp.status_code == 200 else []
    
    def discovery_columns(self, pipeline_id: str, agent_id: str, schema: str, table: str) -> List[Dict]:
        params = {"tableschema": schema, "tablename": table}
        resp = self.request("GET", f"/pipelines/{pipeline_id}/agents/{agent_id}/discovery/columns", params=params)
        return resp.json() if resp.status_code == 200 else []


class OutputFormatter:
    """Format output in different styles"""
    
    @staticmethod
    def format_table(data: List[Dict], columns: List[str]) -> str:
        if not data:
            return "No data found."
        
        # Calculate column widths
        widths = {}
        for col in columns:
            header_len = len(col)
            max_data_len = max(len(str(row.get(col, ""))) for row in data)
            widths[col] = max(header_len, max_data_len) + 2
        
        # Build table
        lines = []
        
        # Header
        header = " ".join(col.upper().ljust(widths[col]) for col in columns)
        lines.append(header)
        lines.append("-" * len(header))
        
        # Data rows
        for row in data:
            row_str = " ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
            lines.append(row_str)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_json(data) -> str:
        return json.dumps(data, indent=2)


class GlueSyncCLI:
    """Main CLI class"""
    
    def __init__(self):
        self.client = None
        self.formatter = OutputFormatter()
    
    def load_config(self, args) -> Config:
        """Load configuration from files and environment"""
        # Determine config path (env var > arg > default)
        if os.getenv("GLUESYNC_CONFIG_PATH"):
            config_path = Path(os.getenv("GLUESYNC_CONFIG_PATH"))
        elif args.config:
            config_path = Path(args.config)
        else:
            config_path = Path(__file__).parent / "config.json"
        
        config_data = {}
        if config_path.exists():
            with open(config_path) as f:
                config_data = json.load(f)
        
        # Load credentials from environment
        # Try to load .env file if python-dotenv is available
        try:
            from dotenv import load_dotenv
            # Determine env path (env var > default)
            if os.getenv("GLUESYNC_ENV_PATH"):
                env_path = Path(os.getenv("GLUESYNC_ENV_PATH"))
            else:
                env_path = Path(__file__).parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
        except ImportError:
            pass
        
        core_hub = config_data.get("core_hub", {})
        
        return Config(
            base_url=core_hub.get("base_url", "https://192.168.13.53:1717"),
            verify_ssl=core_hub.get("verify_ssl", False),
            username=os.getenv("GLUESYNC_ADMIN_USERNAME", "admin"),
            password=os.getenv("GLUESYNC_ADMIN_PASSWORD", ""),
            output_format=args.output if args.output else "table"
        )
    
    def output(self, data, columns: List[str] = None):
        """Output data in configured format"""
        if self.client and self.client.config.output_format == "json":
            print(self.formatter.format_json(data))
        elif columns and isinstance(data, list):
            print(self.formatter.format_table(data, columns))
        else:
            print(self.formatter.format_json(data))
    
    # Pipeline Commands
    def pipeline_list(self, args):
        """List all pipelines"""
        pipelines = self.client.list_pipelines()
        self.output(pipelines, ["id", "name", "description", "configurationCompleted"])
    
    def pipeline_get(self, args):
        """Get pipeline details"""
        pipeline = self.client.get_pipeline(args.pipeline_id)
        if pipeline:
            self.output(pipeline)
        else:
            print(f"Pipeline {args.pipeline_id} not found")
            sys.exit(1)
    
    def pipeline_create(self, args):
        """Create new pipeline"""
        pipeline_id = self.client.create_pipeline(args.name, args.description)
        if pipeline_id:
            print(f"✓ Pipeline created: {pipeline_id}")
        else:
            print("✗ Failed to create pipeline")
            sys.exit(1)
    
    def pipeline_delete(self, args):
        """Delete pipeline"""
        if args.force:
            confirmed = True
        else:
            # Check if running in non-interactive mode (container)
            if not sys.stdin.isatty():
                print(f"Error: Cannot prompt for confirmation in non-interactive mode.")
                print(f"Use --force to delete pipeline {args.pipeline_id} without confirmation.")
                sys.exit(1)
            confirmed = input(f"Delete pipeline {args.pipeline_id}? [y/N]: ").lower() == 'y'
        
        if confirmed:
            if self.client.delete_pipeline(args.pipeline_id):
                print(f"✓ Pipeline {args.pipeline_id} deleted")
            else:
                print("✗ Failed to delete pipeline")
                sys.exit(1)
    
    # Agent Commands
    def agent_list(self, args):
        """List agents in pipeline"""
        agents = self.client.list_agents(args.pipeline_id)
        self.output(agents, ["agentId", "agentType", "status"])
    
    def agent_provision(self, args):
        """Provision new agent"""
        agent_id = self.client.provision_agent(
            args.pipeline_id,
            args.type,
            args.agent_type,
            args.tag
        )
        if agent_id:
            print(f"✓ Agent provisioned: {agent_id}")
            # Auto-assign if role specified
            if args.role:
                if self.client.assign_agent(args.pipeline_id, agent_id, args.role):
                    print(f"✓ Agent assigned as {args.role}")
            print(f"\nNext step: Configure agent credentials")
            print(f"  gluesync-cli agent configure {args.pipeline_id} {agent_id} \\")
            print(f"    --host <host> --port <port> --database <db> \\")
            print(f"    --username <user> --password <pass>")
        else:
            print("✗ Failed to provision agent")
            sys.exit(1)
    
    def agent_configure(self, args):
        """Configure agent credentials"""
        print(f"Configuring agent {args.agent_id}...")
        
        # Configure credentials
        if self.client.configure_agent_credentials(
            args.pipeline_id,
            args.agent_id,
            host=args.host,
            port=args.port,
            database=args.database,
            username=args.username,
            password=args.password,
            trust_cert=args.trust_cert
        ):
            print("✓ Credentials configured")
        else:
            print("✗ Failed to configure credentials")
            sys.exit(1)
        
        # Configure specific settings
        if self.client.configure_agent_specific(args.pipeline_id, args.agent_id):
            print("✓ Agent-specific settings configured")
        else:
            print("⚠ Agent-specific settings may need manual configuration")
        
        print("\n✓ Agent configuration complete")
        print(f"\nTest connection:")
        print(f"  gluesync-cli agent test {args.pipeline_id} {args.agent_id}")
    
    # Entity Commands
    def entity_list(self, args):
        """List entities in pipeline"""
        entities = self.client.list_entities(args.pipeline_id)
        # Extract entity data from nested structure
        flat_entities = []
        for e in entities:
            entity = e.get('entity', {})
            flat_entities.append({
                'entityId': entity.get('entityId'),
                'entityName': entity.get('entityName'),
                'status': 'configured' if entity.get('agentEntities') else 'incomplete'
            })
        self.output(flat_entities, ["entityId", "entityName", "status"])
    
    def entity_get(self, args):
        """Get entity details"""
        entities = self.client.list_entities(args.pipeline_id)
        entity = None
        for e in entities:
            if e.get('entity', {}).get('entityId') == args.entity:
                entity = e
                break
        
        if not entity:
            print(f"Entity {args.entity} not found")
            sys.exit(1)
        
        e = entity.get('entity', {})
        print(f"\n=== Entity Details ===")
        print(f"Entity ID:   {e.get('entityId')}")
        print(f"Name:        {e.get('entityName')}")
        print(f"\n=== Agent Entities ===")
        for ae in e.get('agentEntities', []):
            print(f"\nAgent: {ae.get('agentId')}")
            et = ae.get('entityType', {})
            print(f"  Type: {et.get('type')}")
            if 'allowedOperations' in et:
                print(f"  Allowed Operations: {', '.join(et['allowedOperations'])}")
            if 'snapshotWriteMethod' in et:
                print(f"  Snapshot Write Method: {et['snapshotWriteMethod']}")
            else:
                print(f"  Snapshot Write Method: NOT SET (default: MERGE)")
        print(f"\n=== Keys ===")
        for ae in e.get('agentEntities', []):
            for key in ae.get('keys', []):
                print(f"  {key.get('name')} ({key.get('type')})")
    
    def entity_update(self, args):
        """Update entity configuration (e.g., write method)"""
        if self.client.update_entity_write_method(
            args.pipeline_id, 
            args.entity, 
            args.write_method
        ):
            print(f"✓ Entity {args.entity} updated")
            print(f"  Write Method: {args.write_method}")
        else:
            print("✗ Failed to update entity")
            sys.exit(1)
    
    def entity_start(self, args):
        """Start entity processing"""
        if self.client.start_entity(
            args.pipeline_id,
            args.entity_id,
            with_snapshot=args.with_snapshot,
            snapshot_method=args.snapshot_method
        ):
            print(f"✓ Entity {args.entity_id} started")
            if args.with_snapshot:
                print(f"  Mode: Initial snapshot ({args.snapshot_method})")
        else:
            print("✗ Failed to start entity")
            sys.exit(1)
    
    def entity_stop(self, args):
        """Stop entity processing"""
        if self.client.stop_entity(args.pipeline_id, args.entity_id, args.group):
            print(f"✓ Entity {args.entity_id} stopped")
        else:
            print("✗ Failed to stop entity")
            sys.exit(1)
    
    # Runtime Commands
    def runtime_status(self, args):
        """Show runtime status"""
        pipeline = self.client.get_pipeline(args.pipeline_id)
        if not pipeline:
            print(f"Pipeline {args.pipeline_id} not found")
            sys.exit(1)
        
        entities = self.client.list_entities(args.pipeline_id)
        
        print(f"Pipeline: {pipeline.get('name')} ({args.pipeline_id})")
        print(f"Status: {'✓ Configured' if pipeline.get('configurationCompleted') else '✗ Incomplete'}")
        print(f"\nEntities:")
        for entity in entities:
            print(f"  - {entity.get('entityName')}: {entity.get('status', 'unknown')}")
    
    def agent_types(self, args):
        """List available agent types"""
        agents = self.client.get_available_agents()
        print("\nAvailable Agent Types:")
        print("-" * 60)
        print(f"{'Name':<35} {'Internal Name':<20} {'Role'}")
        print("-" * 60)
        for agent in agents:
            print(f"{agent['name']:<35} {agent['internalName']:<20} {agent['type']}")
        print()
        print("Usage: gluesync-cli agent provision <pipeline-id>")
        print("  --type <source|target>")
        print("  --agent-type <internal-name>")
        print("  --tag <unique-tag>")
    
    # Discovery Commands
    def discovery_schemas(self, args):
        """List schemas from agent"""
        schemas = self.client.discovery_schemas(args.pipeline_id, args.agent_id)
        for schema in schemas:
            print(schema)
    
    def discovery_tables(self, args):
        """List tables from schema"""
        tables = self.client.discovery_tables(args.pipeline_id, args.agent_id, args.schema)
        for table in tables:
            print(table)
    
    def run(self):
        """Main entry point"""
        parser = argparse.ArgumentParser(
            description="GlueSync CLI - Pipeline Management Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  gluesync-cli pipeline list
  gluesync-cli pipeline create --name "My Pipeline"
  gluesync-cli agent list <pipeline-id>
  gluesync-cli entity start <pipeline-id> --entity <entity-id> --with-snapshot
            """
        )
        
        # Global options
        parser.add_argument("--config", "-c", help="Path to config file")
        parser.add_argument("--output", "-o", choices=["table", "json"], default="table",
                          help="Output format")
        parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
        
        subparsers = parser.add_subparsers(dest="command", help="Commands")
        
        # Pipeline commands
        pipeline_parser = subparsers.add_parser("pipeline", help="Pipeline management")
        pipeline_subparsers = pipeline_parser.add_subparsers(dest="subcommand")
        
        # pipeline list
        pipeline_subparsers.add_parser("list", help="List pipelines")
        
        # pipeline get
        pipeline_get_parser = pipeline_subparsers.add_parser("get", help="Get pipeline details")
        pipeline_get_parser.add_argument("pipeline_id", help="Pipeline ID")
        
        # pipeline create
        pipeline_create_parser = pipeline_subparsers.add_parser("create", help="Create pipeline")
        pipeline_create_parser.add_argument("--name", "-n", required=True, help="Pipeline name")
        pipeline_create_parser.add_argument("--description", "-d", default="", help="Description")
        
        # pipeline delete
        pipeline_delete_parser = pipeline_subparsers.add_parser("delete", help="Delete pipeline")
        pipeline_delete_parser.add_argument("pipeline_id", help="Pipeline ID")
        pipeline_delete_parser.add_argument("--force", "-f", action="store_true", help="Force delete")
        
        # Agent commands
        agent_parser = subparsers.add_parser("agent", help="Agent management")
        agent_subparsers = agent_parser.add_subparsers(dest="subcommand")
        
        # agent list
        agent_list_parser = agent_subparsers.add_parser("list", help="List agents")
        agent_list_parser.add_argument("pipeline_id", help="Pipeline ID")
        
        # agent types
        agent_subparsers.add_parser("types", help="List available agent types")
        
        # agent provision
        agent_provision_parser = agent_subparsers.add_parser("provision", help="Provision agent")
        agent_provision_parser.add_argument("pipeline_id", help="Pipeline ID")
        agent_provision_parser.add_argument("--type", choices=["source", "target"], required=True,
                                           help="Agent role type")
        agent_provision_parser.add_argument("--agent-type", required=True,
                                           help="Agent internal type (ibm-iseries, mssql-cdc, etc.)")
        agent_provision_parser.add_argument("--tag", required=True, help="Unique agent tag")
        agent_provision_parser.add_argument("--role", choices=["source", "target"],
                                           help="Auto-assign role after provisioning")
                
        # agent configure
        agent_configure_parser = agent_subparsers.add_parser("configure", help="Configure agent credentials")
        agent_configure_parser.add_argument("pipeline_id", help="Pipeline ID")
        agent_configure_parser.add_argument("agent_id", help="Agent ID")
        agent_configure_parser.add_argument("--host", required=True, help="Database host")
        agent_configure_parser.add_argument("--port", type=int, default=0, help="Database port (0 for default)")
        agent_configure_parser.add_argument("--database", "-d", required=True, help="Database name")
        agent_configure_parser.add_argument("--username", "-u", required=True, help="Database username")
        agent_configure_parser.add_argument("--password", "-p", required=True, help="Database password")
        agent_configure_parser.add_argument("--trust-cert", action="store_true", 
                                           help="Trust server certificate (for SSL)")
                
        # Entity Commands
        entity_parser = subparsers.add_parser("entity", help="Entity management")
        entity_subparsers = entity_parser.add_subparsers(dest="subcommand")
        
        # entity list
        entity_list_parser = entity_subparsers.add_parser("list", help="List entities")
        entity_list_parser.add_argument("pipeline_id", help="Pipeline ID")
        
        # entity get
        entity_get_parser = entity_subparsers.add_parser("get", help="Get entity details")
        entity_get_parser.add_argument("pipeline_id", help="Pipeline ID")
        entity_get_parser.add_argument("--entity", "-e", required=True, help="Entity ID")
        
        # entity update
        entity_update_parser = entity_subparsers.add_parser("update", help="Update entity configuration")
        entity_update_parser.add_argument("pipeline_id", help="Pipeline ID")
        entity_update_parser.add_argument("--entity", "-e", required=True, help="Entity ID")
        entity_update_parser.add_argument("--write-method", "-w", 
                                          choices=["MERGE", "UPSERT", "INSERT"],
                                          required=True, help="Snapshot write method")
        
        # entity start
        entity_start_parser = entity_subparsers.add_parser("start", help="Start entity")
        entity_start_parser.add_argument("pipeline_id", help="Pipeline ID")
        entity_start_parser.add_argument("--entity", "-e", required=True, help="Entity ID")
        entity_start_parser.add_argument("--with-snapshot", action="store_true", default=True,
                                        help="Include initial snapshot")
        entity_start_parser.add_argument("--snapshot-method", default="UPSERT",
                                        choices=["UPSERT", "INSERT"],
                                        help="Snapshot write method")
        
        # entity stop
        entity_stop_parser = entity_subparsers.add_parser("stop", help="Stop entity")
        entity_stop_parser.add_argument("pipeline_id", help="Pipeline ID")
        entity_stop_parser.add_argument("--entity", "-e", required=True, help="Entity ID")
        entity_stop_parser.add_argument("--group", default="_default", help="Entity group ID")
        
        # Runtime commands
        runtime_parser = subparsers.add_parser("runtime", help="Runtime operations")
        runtime_subparsers = runtime_parser.add_subparsers(dest="subcommand")
        
        # runtime status
        runtime_status_parser = runtime_subparsers.add_parser("status", help="Show runtime status")
        runtime_status_parser.add_argument("pipeline_id", help="Pipeline ID")
        
        # Discovery commands
        discovery_parser = subparsers.add_parser("discovery", help="Schema discovery")
        discovery_subparsers = discovery_parser.add_subparsers(dest="subcommand")
        
        # discovery schemas
        discovery_schemas_parser = discovery_subparsers.add_parser("schemas", help="List schemas")
        discovery_schemas_parser.add_argument("pipeline_id", help="Pipeline ID")
        discovery_schemas_parser.add_argument("--agent", "-a", required=True, help="Agent ID")
        
        # discovery tables
        discovery_tables_parser = discovery_subparsers.add_parser("tables", help="List tables")
        discovery_tables_parser.add_argument("pipeline_id", help="Pipeline ID")
        discovery_tables_parser.add_argument("--agent", "-a", required=True, help="Agent ID")
        discovery_tables_parser.add_argument("--schema", "-s", required=True, help="Schema name")
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            sys.exit(1)
        
        # Load config and create client
        config = self.load_config(args)
        if not config.password:
            print("Error: Admin password not set. Set GLUESYNC_ADMIN_PASSWORD environment variable.")
            sys.exit(1)
        
        try:
            self.client = GlueSyncClient(config)
        except Exception as e:
            print(f"Error connecting to GlueSync: {e}")
            sys.exit(1)
        
        # Route to command handler
        handler_name = f"{args.command}_{args.subcommand}" if args.subcommand else args.command
        handler = getattr(self, handler_name, None)
        
        if handler:
            handler(args)
        else:
            print(f"Unknown command: {handler_name}")
            sys.exit(1)


if __name__ == "__main__":
    cli = GlueSyncCLI()
    cli.run()

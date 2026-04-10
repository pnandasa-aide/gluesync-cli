#!/usr/bin/env python3
"""
Recreate AS400-to-MSSQL Pipeline with Agent Provisioning
This script recreates the complete pipeline with agents and entities
Uses config.json for settings and .env for credentials

Setup:
1. Copy .env.example to .env
2. Fill in your credentials in .env
3. Modify config.json for your environment settings
4. Run: python3 recreate_pipeline_secure.py
"""

import requests
import json
import sys
import os
import urllib3
from pathlib import Path

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, 'r') as f:
        return json.load(f)


def load_credentials():
    """Load credentials from environment variables"""
    # Try to load .env file if python-dotenv is available
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass  # python-dotenv not installed, use system env vars
    
    credentials = {
        'admin_username': os.getenv('GLUESYNC_ADMIN_USERNAME', 'admin'),
        'admin_password': os.getenv('GLUESYNC_ADMIN_PASSWORD'),
        'as400_username': os.getenv('AS400_USER'),
        'as400_password': os.getenv('AS400_PASSWORD'),
        'mssql_username': os.getenv('MSSQL_USER'),
        'mssql_password': os.getenv('MSSQL_PASSWORD'),
    }
    
    # Validate required credentials
    missing = [k for k, v in credentials.items() if v is None]
    if missing:
        print("Error: Missing required environment variables:")
        for key in missing:
            print(f"  - {key}")
        print("\nPlease set them in your .env file or environment.")
        print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)
    
    return credentials


class PipelineRecreator:
    def __init__(self, config, credentials):
        self.config = config
        self.credentials = credentials
        self.base_url = config['core_hub']['base_url']
        self.verify_ssl = config['core_hub'].get('verify_ssl', False)
        self.token = None
        self.source_agent_id = None
        self.target_agent_id = None
        self._auth()
    
    def _auth(self):
        """Authenticate and obtain API token"""
        resp = requests.post(
            f"{self.base_url}/authentication/login",
            json={
                "username": self.credentials['admin_username'],
                "password": self.credentials['admin_password']
            },
            verify=self.verify_ssl
        )
        self.token = resp.json()["apiToken"]
        print("✓ Authenticated")
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def provision_agent(self, pipeline_id, agent_config, agent_user_tag):
        """
        Provision a new agent for the pipeline
        
        Args:
            pipeline_id: The pipeline ID
            agent_config: Agent configuration from config.json
            agent_user_tag: Unique tag for this agent instance
        
        Returns:
            agent_id: The newly provisioned agent ID
        """
        url = f"{self.base_url}/pipelines/{pipeline_id}/agents/add"
        params = {
            "agentType": agent_config['agent_type'],
            "agentInternalName": agent_config['agent_internal_name'],
            "agentUserTag": agent_user_tag
        }
        
        resp = requests.get(
            url, 
            headers=self._headers(), 
            params=params, 
            verify=self.verify_ssl
        )
        
        if resp.status_code == 200:
            result = resp.json()
            agent_id = result.get("agentId")
            print(f"  ✓ Agent provisioned: {agent_id} ({agent_config['agent_internal_name']})")
            return agent_id
        else:
            print(f"  ✗ Failed to provision agent: {resp.text}")
            return None
    
    def assign_agent(self, pipeline_id, agent_id, agent_type):
        """Assign agent to pipeline"""
        url = f"{self.base_url}/pipelines/{pipeline_id}/agents/{agent_id}"
        params = {"agentType": agent_type.upper()}
        
        resp = requests.put(
            url, 
            headers=self._headers(), 
            params=params, 
            verify=self.verify_ssl
        )
        
        if resp.status_code == 200:
            print(f"  ✓ Agent assigned to pipeline")
            return True
        else:
            print(f"  ✗ Failed to assign agent: {resp.text}")
            return False
    
    def configure_agent_credentials(self, pipeline_id, agent_id, agent_config, username, password):
        """Configure agent connection credentials"""
        url = f"{self.base_url}/pipelines/{pipeline_id}/agents/{agent_id}/config/credentials"
        
        conn = agent_config['connection']
        credentials = {
            "hostCredentials": {
                "connectionName": "",
                "host": conn['host'],
                "port": conn['port'],
                "databaseName": conn.get('database_name', ''),
                "username": username,
                "password": password,
                "disableAuth": False,
                "enableTls": False,
                "trustServerCertificate": conn.get('trust_server_certificate', False),
                "useUploadedTrustStore": False,
                "useUploadedKeyStore": False,
                "useUploadedCertificate": False,
                "additionalHosts": [{"host": ""}],
                "minConnectionsCount": 5,
                "maxConnectionsCount": 25
            }
        }
        
        resp = requests.put(
            url, 
            headers=self._headers(), 
            json=credentials, 
            verify=self.verify_ssl
        )
        
        if resp.status_code == 202:
            print(f"  ✓ Credentials configured")
            return True
        else:
            print(f"  ✗ Failed to configure credentials: {resp.text}")
            return False
    
    def configure_agent_specific(self, pipeline_id, agent_id):
        """Configure agent-specific settings"""
        url = f"{self.base_url}/pipelines/{pipeline_id}/agents/{agent_id}/config/specific"
        
        config = {"configuration": {}}
        
        resp = requests.put(
            url, 
            headers=self._headers(), 
            json=config, 
            verify=self.verify_ssl
        )
        
        if resp.status_code == 202:
            print(f"  ✓ Agent-specific settings configured")
            return True
        else:
            print(f"  ✗ Failed to configure agent settings: {resp.text}")
            return False
    
    def recreate_pipeline(self):
        """Main pipeline recreation workflow"""
        
        # Step 1: Create empty pipeline
        print("\n1. Creating pipeline...")
        pipeline_config = self.config['pipeline']
        
        resp = requests.post(
            f"{self.base_url}/pipelines",
            headers=self._headers(),
            json=pipeline_config,
            verify=self.verify_ssl
        )
        result = resp.json()
        pipeline_id = result.get("pipelineId")
        print(f"✓ Pipeline created: {pipeline_id}")
        
        # Step 2: Provision and configure source agent
        source_config = self.config['source_agent']
        print(f"\n2. Provisioning source agent ({source_config['agent_internal_name']})...")
        
        self.source_agent_id = self.provision_agent(
            pipeline_id=pipeline_id,
            agent_config=source_config,
            agent_user_tag=source_config['agent_user_tag']
        )
        
        if not self.source_agent_id:
            print("✗ Failed to provision source agent")
            return None
        
        self.assign_agent(pipeline_id, self.source_agent_id, "SOURCE")
        
        self.configure_agent_credentials(
            pipeline_id=pipeline_id,
            agent_id=self.source_agent_id,
            agent_config=source_config,
            username=self.credentials['as400_username'],
            password=self.credentials['as400_password']
        )
        
        self.configure_agent_specific(pipeline_id, self.source_agent_id)
        
        # Step 3: Provision and configure target agent
        target_config = self.config['target_agent']
        print(f"\n3. Provisioning target agent ({target_config['agent_internal_name']})...")
        
        self.target_agent_id = self.provision_agent(
            pipeline_id=pipeline_id,
            agent_config=target_config,
            agent_user_tag=target_config['agent_user_tag']
        )
        
        if not self.target_agent_id:
            print("✗ Failed to provision target agent")
            return None
        
        self.assign_agent(pipeline_id, self.target_agent_id, "TARGET")
        
        self.configure_agent_credentials(
            pipeline_id=pipeline_id,
            agent_id=self.target_agent_id,
            agent_config=target_config,
            username=self.credentials['mssql_username'],
            password=self.credentials['mssql_password']
        )
        
        self.configure_agent_specific(pipeline_id, self.target_agent_id)
        
        print(f"\n✅ Pipeline {pipeline_id} recreated successfully!")
        print(f"   Source Agent: {self.source_agent_id}")
        print(f"   Target Agent: {self.target_agent_id}")
        
        return pipeline_id


if __name__ == "__main__":
    # Load configuration and credentials
    config = load_config()
    credentials = load_credentials()
    
    # Create and run recreator
    recreator = PipelineRecreator(config, credentials)
    pipeline_id = recreator.recreate_pipeline()
    
    if pipeline_id:
        print(f"\nNext steps:")
        print(f"  - Access UI: {config['core_hub']['base_url']}/ui/index.html")
        print(f"  - Pipeline ID: {pipeline_id}")
        print(f"  - Add entities via UI or API")

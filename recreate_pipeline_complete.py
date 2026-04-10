#!/usr/bin/env python3
"""
Recreate AS400-to-MSSQL Pipeline with Agent Provisioning
This script recreates the complete pipeline with agents and entities
Based on captured API calls from MITM proxy analysis

SECURITY NOTICE: Replace all placeholder credentials marked with < > before use:
- <ADMIN_PASSWORD> - Core Hub admin password
- <AS400_USER>, <AS400_PASSWORD> - AS400 credentials  
- <MSSQL_USER>, <MSSQL_PASSWORD> - MSSQL credentials
"""

import requests
import json
import sys
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PipelineRecreator:
    def __init__(self, base_url="https://192.168.13.53:1717", username="admin", password="<ADMIN_PASSWORD>"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.source_agent_id = None
        self.target_agent_id = None
        self._auth()
    
    def _auth(self):
        """Authenticate and obtain API token"""
        resp = requests.post(
            f"{self.base_url}/authentication/login",
            json={"username": self.username, "password": self.password},
            verify=False
        )
        self.token = resp.json()["apiToken"]
        print("✓ Authenticated")
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def provision_agent(self, pipeline_id, agent_type, agent_internal_name, agent_user_tag):
        """
        Provision a new agent for the pipeline
        
        Args:
            pipeline_id: The pipeline ID
            agent_type: "source" or "target"
            agent_internal_name: "ibm-iseries", "mssql-cdc", etc.
            agent_user_tag: A unique tag for this agent instance
        
        Returns:
            agent_id: The newly provisioned agent ID
        """
        url = f"{self.base_url}/pipelines/{pipeline_id}/agents/add"
        params = {
            "agentType": agent_type,
            "agentInternalName": agent_internal_name,
            "agentUserTag": agent_user_tag
        }
        
        resp = requests.get(url, headers=self._headers(), params=params, verify=False)
        
        if resp.status_code == 200:
            result = resp.json()
            agent_id = result.get("agentId")
            print(f"  ✓ Agent provisioned: {agent_id} ({agent_internal_name})")
            return agent_id
        else:
            print(f"  ✗ Failed to provision agent: {resp.text}")
            return None
    
    def assign_agent(self, pipeline_id, agent_id, agent_type):
        """Assign agent to pipeline"""
        url = f"{self.base_url}/pipelines/{pipeline_id}/agents/{agent_id}"
        params = {"agentType": agent_type.upper()}
        
        resp = requests.put(url, headers=self._headers(), params=params, verify=False)
        
        if resp.status_code == 200:
            print(f"  ✓ Agent assigned to pipeline")
            return True
        else:
            print(f"  ✗ Failed to assign agent: {resp.text}")
            return False
    
    def configure_agent_credentials(self, pipeline_id, agent_id, host, username, password, 
                                     database_name="", port=0, trust_server_cert=False):
        """Configure agent connection credentials"""
        url = f"{self.base_url}/pipelines/{pipeline_id}/agents/{agent_id}/config/credentials"
        
        credentials = {
            "hostCredentials": {
                "connectionName": "",
                "host": host,
                "port": port,
                "databaseName": database_name,
                "username": username,
                "password": password,
                "disableAuth": False,
                "enableTls": False,
                "trustServerCertificate": trust_server_cert,
                "useUploadedTrustStore": False,
                "useUploadedKeyStore": False,
                "useUploadedCertificate": False,
                "additionalHosts": [{"host": ""}],
                "minConnectionsCount": 5,
                "maxConnectionsCount": 25
            }
        }
        
        resp = requests.put(url, headers=self._headers(), json=credentials, verify=False)
        
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
        
        resp = requests.put(url, headers=self._headers(), json=config, verify=False)
        
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
        pipeline_config = {
            "name": "AS400-to-MSSQL-Pipeline",
            "description": "Sync data from AS400 DB2 to Microsoft SQL Server",
            "enabled": True
        }
        
        resp = requests.post(
            f"{self.base_url}/pipelines",
            headers=self._headers(),
            json=pipeline_config,
            verify=False
        )
        result = resp.json()
        pipeline_id = result.get("pipelineId")
        print(f"✓ Pipeline created: {pipeline_id}")
        
        # Step 2: Provision and configure source agent (ibm-iseries)
        print("\n2. Provisioning source agent (ibm-iseries)...")
        self.source_agent_id = self.provision_agent(
            pipeline_id=pipeline_id,
            agent_type="source",
            agent_internal_name="ibm-iseries",
            agent_user_tag="source-ibm-iseries"
        )
        
        if not self.source_agent_id:
            print("✗ Failed to provision source agent")
            return None
        
        self.assign_agent(pipeline_id, self.source_agent_id, "SOURCE")
        
        self.configure_agent_credentials(
            pipeline_id=pipeline_id,
            agent_id=self.source_agent_id,
            host="161.82.146.249",
            username="<AS400_USER>",
            password="<AS400_PASSWORD>",
            database_name="GSLIBTST",
            port=0,
            trust_server_cert=False
        )
        
        self.configure_agent_specific(pipeline_id, self.source_agent_id)
        
        # Step 3: Provision and configure target agent (mssql-cdc)
        print("\n3. Provisioning target agent (mssql-cdc)...")
        self.target_agent_id = self.provision_agent(
            pipeline_id=pipeline_id,
            agent_type="target",
            agent_internal_name="mssql-cdc",
            agent_user_tag="target-mssql-cdc"
        )
        
        if not self.target_agent_id:
            print("✗ Failed to provision target agent")
            return None
        
        self.assign_agent(pipeline_id, self.target_agent_id, "TARGET")
        
        self.configure_agent_credentials(
            pipeline_id=pipeline_id,
            agent_id=self.target_agent_id,
            host="192.168.13.62",
            username="<MSSQL_USER>",
            password="<MSSQL_PASSWORD>",
            database_name="GSTargetDB",
            port=0,
            trust_server_cert=True
        )
        
        self.configure_agent_specific(pipeline_id, self.target_agent_id)
        
        print(f"\n✅ Pipeline {pipeline_id} recreated successfully!")
        print(f"   Source Agent: {self.source_agent_id}")
        print(f"   Target Agent: {self.target_agent_id}")
        
        return pipeline_id


if __name__ == "__main__":
    recreator = PipelineRecreator()
    pipeline_id = recreator.recreate_pipeline()
    
    if pipeline_id:
        print(f"\nNext steps:")
        print(f"  - Access UI: https://192.168.13.53:1717/ui/index.html")
        print(f"  - Pipeline ID: {pipeline_id}")
        print(f"  - Add entities via UI or API")

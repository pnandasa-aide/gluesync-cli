#!/usr/bin/env python3
"""
MITM Proxy addon to capture GlueSync API calls
Usage: mitmproxy -s capture_api.py --mode reverse:https://192.168.13.53:1717 --listen-port 1718
"""

import json
import os
from datetime import datetime
from mitmproxy import http

# Log file for captured API calls
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captured_api_calls.json")

def load_existing_logs():
    """Load existing logs if file exists"""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_logs(logs):
    """Save logs to file"""
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

class APICapture:
    def __init__(self):
        self.logs = load_existing_logs()
        print(f"Loaded {len(self.logs)} existing log entries")
    
    def request(self, flow: http.HTTPFlow) -> None:
        """Capture request details"""
        # Only capture API calls (not static assets)
        if not any(flow.request.path.startswith(p) for p in ['/pipelines', '/authentication', '/agents', '/api/']):
            return
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "method": flow.request.method,
            "url": flow.request.url,
            "path": flow.request.path,
            "headers": dict(flow.request.headers),
        }
        
        # Capture request body
        if flow.request.content:
            try:
                body = flow.request.content.decode('utf-8')
                entry["request_body"] = json.loads(body) if body else None
            except:
                entry["request_body_raw"] = flow.request.content.hex()[:200]
        
        # Store temporarily in metadata
        flow.metadata["capture_entry"] = entry
    
    def response(self, flow: http.HTTPFlow) -> None:
        """Capture response details"""
        if "capture_entry" not in flow.metadata:
            return
        
        entry = flow.metadata["capture_entry"]
        entry["status_code"] = flow.response.status_code
        entry["response_headers"] = dict(flow.response.headers)
        
        # Capture response body
        if flow.response.content:
            try:
                body = flow.response.content.decode('utf-8')
                entry["response_body"] = json.loads(body) if body else None
            except:
                entry["response_body_raw"] = flow.response.content.hex()[:200]
        
        # Add to logs
        self.logs.append(entry)
        save_logs(self.logs)
        
        # Print to console
        print(f"\n[{entry['method']}] {entry['path']} -> {entry['status_code']}")
        if 'request_body' in entry:
            print(f"Request: {json.dumps(entry['request_body'], indent=2)[:200]}")
        if 'response_body' in entry:
            print(f"Response: {json.dumps(entry['response_body'], indent=2)[:200]}")

# Create addon instance
addons = [APICapture()]

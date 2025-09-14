#!/usr/bin/env python3
"""
Poke Integration Test Script
Tests the MCP server integration with Poke and diagnoses any issues
"""

import os
import requests
import json
import time
from datetime import datetime

# Your Poke API credentials
POKE_API_KEY = "pk_wsnMs_5gWmDJnxnpMtwhQmmOpfdEaCNHP9CIkoWQMTM"
POKE_API_URL = "https://poke.com/api/v1/inbound-sms/webhook"

# Your MCP server details
MCP_SERVER_URL = "https://poke-trello-mcp.onrender.com/mcp"
MCP_AUTH_TOKEN = "0USbNEFqvtn3cWCmj4KsVwyrH598QDZh"

def send_poke_message(message):
    """Send a message to Poke to test MCP integration"""
    headers = {
        'Authorization': f'Bearer {POKE_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'message': message
    }
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sending to Poke: {message}")
    
    try:
        response = requests.post(POKE_API_URL, headers=headers, json=data)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def test_mcp_direct():
    """Test the MCP server directly to ensure it's working"""
    print("\n" + "="*50)
    print("Testing MCP Server Directly")
    print("="*50)
    
    # Test health endpoint
    try:
        health_url = MCP_SERVER_URL.replace('/mcp', '/health')
        response = requests.get(health_url)
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"Health response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test MCP endpoint with JSON-RPC
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # JSON-RPC request to list tools
    json_rpc_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 1
    }
    
    url_with_auth = f"{MCP_SERVER_URL}?token={MCP_AUTH_TOKEN}"
    
    print(f"\nTesting JSON-RPC at: {url_with_auth}")
    try:
        response = requests.post(url_with_auth, headers=headers, json=json_rpc_request)
        print(f"JSON-RPC Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        if response.status_code == 200:
            print(f"Response: {response.text[:500]}")  # First 500 chars
        else:
            print(f"Error Response: {response.text}")
    except Exception as e:
        print(f"JSON-RPC test failed: {e}")

def test_poke_commands():
    """Test various Poke commands that should trigger MCP tools"""
    print("\n" + "="*50)
    print("Testing Poke Commands")
    print("="*50)
    
    test_messages = [
        "clearhistory",  # Reset Poke session
        "Show all my Trello boards",
        "List all lists on my active Trello board",
        "What Trello cards are assigned to me?",
        "Show recent activity on my Trello board"
    ]
    
    for message in test_messages:
        result = send_poke_message(message)
        time.sleep(3)  # Wait between messages to avoid rate limiting

def diagnose_connection():
    """Diagnose the connection between Poke and MCP"""
    print("\n" + "="*50)
    print("Connection Diagnosis")
    print("="*50)
    
    # First, ask Poke about its connections
    send_poke_message("What integrations do you have connected?")
    time.sleep(3)
    
    # Try to get Poke to explicitly use the MCP connection
    send_poke_message(f"Connect to MCP server at {MCP_SERVER_URL}")
    time.sleep(3)
    
    # Test if Poke recognizes Trello commands
    send_poke_message("Do you have access to Trello tools?")

def check_server_logs():
    """Instructions for checking server logs"""
    print("\n" + "="*50)
    print("Server Log Check Instructions")
    print("="*50)
    print("""
    To debug further, check your Render logs:
    
    1. Go to https://dashboard.render.com/
    2. Click on your 'poke-trello-mcp' service
    3. Go to the 'Logs' tab
    4. Look for:
       - Incoming requests from Poke
       - Authentication errors
       - Content-Type headers
       - Any 400/406 errors
    
    Key things to look for:
    - Are requests reaching your server?
    - What Accept header is Poke sending?
    - Are there authentication failures?
    """)

def main():
    print("""
    ╔══════════════════════════════════════════════════╗
    ║     Poke MCP Integration Diagnostic Tool        ║
    ╚══════════════════════════════════════════════════╝
    """)
    
    print(f"MCP Server: {MCP_SERVER_URL}")
    print(f"Auth Token: {MCP_AUTH_TOKEN[:10]}...")
    
    # Run all tests
    test_mcp_direct()
    test_poke_commands()
    diagnose_connection()
    check_server_logs()
    
    print("\n" + "="*50)
    print("Diagnostic Complete")
    print("="*50)
    print("""
    Next steps:
    1. Check the Render logs for your service
    2. Verify the MCP connection in Poke settings
    3. If still having issues, the problem might be:
       - Content negotiation (SSE vs JSON)
       - Authentication token format
       - URL configuration in Poke
    """)

if __name__ == "__main__":
    main()
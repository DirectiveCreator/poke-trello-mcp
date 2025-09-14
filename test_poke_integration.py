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
MCP_SERVER_URL = "https://poke-trello-mcp.onrender.com/mcp"  # Note: /mcp endpoint
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
    
    # Test root endpoint
    try:
        root_url = "https://poke-trello-mcp.onrender.com/"
        response = requests.get(root_url)
        print(f"Root endpoint /: {response.status_code}")
    except Exception as e:
        print(f"Root check failed: {e}")
    
    # Test MCP endpoint with different methods
    url_with_auth = f"{MCP_SERVER_URL}?token={MCP_AUTH_TOKEN}"
    
    # Test 1: GET request (SSE)
    print(f"\nTest 1: GET {url_with_auth}")
    try:
        headers = {'Accept': 'text/event-stream'}
        response = requests.get(url_with_auth, headers=headers, stream=True)
        print(f"GET Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        if response.status_code == 200:
            # Read first few lines of SSE stream
            lines = []
            for i, line in enumerate(response.iter_lines()):
                if i >= 5:  # Only read first 5 lines
                    break
                lines.append(line.decode('utf-8') if line else '')
            print(f"SSE Response (first 5 lines): {lines}")
    except Exception as e:
        print(f"GET test failed: {e}")
    
    # Test 2: POST with JSON-RPC
    print(f"\nTest 2: POST JSON-RPC to {url_with_auth}")
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    json_rpc_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 1
    }
    
    try:
        response = requests.post(url_with_auth, headers=headers, json=json_rpc_request)
        print(f"POST Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        if response.status_code == 200:
            print(f"Response: {response.text[:500]}")  # First 500 chars
        else:
            print(f"Error Response: {response.text}")
    except Exception as e:
        print(f"POST test failed: {e}")
    
    # Test 3: Test without auth token
    print(f"\nTest 3: Testing authentication requirement")
    try:
        response = requests.post(MCP_SERVER_URL, headers=headers, json=json_rpc_request)
        print(f"No auth status: {response.status_code}")
        if response.status_code == 401:
            print("✓ Authentication properly enforced")
        else:
            print(f"Warning: Got {response.status_code} without auth token")
    except Exception as e:
        print(f"Auth test failed: {e}")

def test_poke_commands():
    """Test various Poke commands that should trigger MCP tools"""
    print("\n" + "="*50)
    print("Testing Poke Commands")
    print("="*50)
    
    test_messages = [
        "clearhistory",  # Reset Poke session
        "What MCP integrations do you have?",
        "Can you connect to the Trello MCP server?",
        "List my Trello boards using the MCP integration",
    ]
    
    for message in test_messages:
        result = send_poke_message(message)
        time.sleep(5)  # Wait longer between messages

def diagnose_connection():
    """Diagnose the connection between Poke and MCP"""
    print("\n" + "="*50)
    print("Connection Diagnosis")
    print("="*50)
    
    # Try different connection methods
    test_urls = [
        f"https://poke-trello-mcp.onrender.com/mcp?token={MCP_AUTH_TOKEN}",
        f"https://poke-trello-mcp.onrender.com/mcp",
        "https://poke-trello-mcp.onrender.com",
    ]
    
    for url in test_urls:
        print(f"\nAsking Poke to connect to: {url}")
        send_poke_message(f"Connect to MCP server at {url}")
        time.sleep(5)
        
        # Test if connection worked
        send_poke_message("Can you list my Trello boards?")
        time.sleep(5)

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
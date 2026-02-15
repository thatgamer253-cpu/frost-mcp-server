"""
Test script to verify MCP server functionality
"""

import subprocess
import json
import sys

def test_mcp_server():
    """Test the MCP server by sending requests."""
    
    print("Testing Frost MCP Server...")
    print("=" * 50)
    
    # Start the server
    process = subprocess.Popen(
        [sys.executable, "frost_mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send initialization request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    print("\n1. Sending initialization request...")
    process.stdin.write(json.dumps(init_request) + "\n")
    process.stdin.flush()
    
    # Read response
    response = process.stdout.readline()
    print(f"Response: {response[:100]}...")
    
    # List tools request
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    print("\n2. Requesting tool list...")
    process.stdin.write(json.dumps(list_tools_request) + "\n")
    process.stdin.flush()
    
    response = process.stdout.readline()
    print(f"Response: {response[:200]}...")
    
    # Terminate
    process.terminate()
    process.wait(timeout=5)
    
    print("\n" + "=" * 50)
    print("Test complete!")

if __name__ == "__main__":
    test_mcp_server()

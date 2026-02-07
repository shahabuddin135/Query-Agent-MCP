"""Quick test for the Streamable HTTP MCP server."""
import urllib.request
import json

url = "http://localhost:8000/mcp"

# Test 1: Initialize
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"}
    }
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

print("=== Test: MCP Initialize ===")
try:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    resp = urllib.request.urlopen(req)
    print(f"Status: {resp.status}")
    body = resp.read().decode("utf-8")
    data = json.loads(body)
    print(json.dumps(data, indent=2))
    
    # Get session ID from response headers
    session_id = resp.headers.get("Mcp-Session-Id")
    print(f"\nSession ID: {session_id}")
    
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode("utf-8"))
except Exception as e:
    print(f"Error: {e}")

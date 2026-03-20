import httpx
import json

url = "https://intune-mcp-app.livelybeach-a07d25bc.swedencentral.azurecontainerapps.io/mcp"

r = httpx.post(url, json={
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "clientInfo": {"name": "test", "version": "1.0"}, "capabilities": {}}
})
sid = r.headers.get("mcp-session-id", "")

r2 = httpx.post(url, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                headers={"mcp-session-id": sid})
tools = r2.json()["result"]["tools"]
print(f"Total tools: {len(tools)}")
for t in tools:
    print(f"  - {t['name']}: {t['description'][:60]}...")

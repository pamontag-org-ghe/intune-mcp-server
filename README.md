# Intune MCP Server

An MCP (Model Context Protocol) server that exposes Microsoft Intune capabilities via the Graph API. Built with FastAPI and deployed as a Streamable HTTP endpoint on Azure Container Apps.

## Features

- **Get Devices by UPN** – Retrieve Intune managed devices for a user by their User Principal Name.
- **Get Policies by Device ID** – Retrieve configuration policies applied to a specific managed device.
- **Streamable HTTP MCP transport** – Standards-compliant MCP endpoint at `/mcp`.
- **Application Insights** – Built-in telemetry via Azure Monitor OpenTelemetry.
- **Azure Container Apps** – Serverless deployment with auto-scaling.

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── auth.py           # MSAL token acquisition for Graph API
│   ├── config.py         # Settings from environment variables
│   ├── graph_client.py   # Intune Graph API calls
│   └── main.py           # FastAPI app with MCP JSON-RPC endpoint
├── infra/
│   └── main.bicep        # Azure infrastructure (Container Apps, App Insights)
├── UseCases/
│   └── UseCase_GetPoliciesByDevices.md
├── deploy.sh             # Deployment script (bash)
├── deploy.ps1            # Deployment script (PowerShell)
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Prerequisites

- Python 3.12+
- Docker
- Azure CLI (`az`) logged in
- An Azure AD App Registration with the following **Application permissions** on Microsoft Graph:
  - `DeviceManagementManagedDevices.Read.All`
  - `DeviceManagementConfiguration.Read.All`

## Local Development

1. Copy `.env.example` to `.env` and fill in your credentials:

   ```
   cp .env.example .env
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Run the server:

   ```
   uvicorn app.main:app --reload
   ```

4. Health check: `GET http://localhost:8000/health`

5. MCP endpoint: `POST http://localhost:8000/mcp`

## MCP Tools

### `get_devices_by_upn`

Retrieve managed devices for a user.

| Parameter | Type   | Required | Description                       |
|-----------|--------|----------|-----------------------------------|
| `upn`     | string | Yes      | User Principal Name (e.g. user@contoso.com) |

### `get_policies_by_device_id`

Retrieve configuration policies applied to a device.

| Parameter   | Type   | Required | Description              |
|-------------|--------|----------|--------------------------|
| `device_id` | string | Yes      | Intune device ID (GUID)  |

## Deploy to Azure

### PowerShell

```powershell
.\deploy.ps1 `
    -ResourceGroup "rg-intune-mcp" `
    -AcrName "youracrname" `
    -TenantId "<tenant-id>" `
    -ClientId "<client-id>" `
    -ClientSecret "<client-secret>"
```

### Bash

```bash
./deploy.sh \
    --resource-group rg-intune-mcp \
    --acr-name youracrname \
    --tenant-id <tenant-id> \
    --client-id <client-id> \
    --client-secret <client-secret>
```

The deployment script will:
1. Create a resource group
2. Create an Azure Container Registry and push the Docker image
3. Deploy infrastructure via Bicep (Log Analytics, Application Insights, Container Apps Environment, Container App)
4. Output the MCP endpoint URL

## MCP Client Configuration

After deployment, configure your MCP client to connect to the server:

```json
{
  "mcpServers": {
    "intune": {
      "url": "https://<your-container-app-fqdn>/mcp"
    }
  }
}
```

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.config import settings
from app.graph_client import (
    get_apps_by_device,
    get_app_install_status,
    get_autopilot_device,
    get_compliance_policies_by_device,
    get_conditional_access_policies,
    get_devices_by_upn,
    get_intune_apps,
    get_policies_by_device_id,
    get_users_by_display_name,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions exposed via MCP
# ---------------------------------------------------------------------------
TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_devices_by_upn",
        "description": (
            "Retrieve Intune managed devices for a user identified by their "
            "User Principal Name (UPN). Returns a list of managed device objects "
            "including device id, device name, OS, compliance state, and more."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "upn": {
                    "type": "string",
                    "description": "The User Principal Name (email) of the user, e.g. user@contoso.com",
                }
            },
            "required": ["upn"],
        },
    },
    {
        "name": "get_policies_by_device_id",
        "description": (
            "Retrieve Intune configuration policies applied to a specific device. "
            "Requires the Intune device ID. Returns policy names, types, statuses, "
            "and other metadata."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Intune device ID (GUID) of the managed device.",
                }
            },
            "required": ["device_id"],
        },
    },
    {
        "name": "get_users_by_display_name",
        "description": (
            "Search for users by display name with fuzzy matching (startsWith). "
            "Use this when you don't know the exact UPN but know part of the user's "
            "display name. Returns user ID, display name, UPN, and email for each match. "
            "Handles multiple matches, no matches, and partial name searches."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "display_name": {
                    "type": "string",
                    "description": "The display name (or beginning of it) to search for, e.g. 'Mickey' or 'Mickey Mouse'.",
                }
            },
            "required": ["display_name"],
        },
    },
    {
        "name": "get_apps_by_device",
        "description": (
            "Retrieve applications assigned to a specific device and their installation states. "
            "Requires the user ID (GUID) and the Intune device ID (GUID). "
            "Returns app names, install state, supported device types, and error details for apps in error."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The Azure AD user ID (GUID) of the device owner.",
                },
                "device_id": {
                    "type": "string",
                    "description": "The Intune device ID (GUID) of the managed device.",
                },
            },
            "required": ["user_id", "device_id"],
        },
    },
    {
        "name": "get_intune_apps",
        "description": (
            "List all applications distributed by Intune. "
            "Returns app ID, display name, publisher, creation date, and assignment status. "
            "Use this to discover which apps are managed and distributed through Intune."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_app_install_status",
        "description": (
            "Troubleshoot application installation errors. Retrieves the device-level "
            "installation status report for a specific Intune application. "
            "Returns device name, user, platform, install state, error codes (decimal and hex), "
            "and detailed error descriptions. Use this to diagnose why an app is failing to install."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "application_id": {
                    "type": "string",
                    "description": "The Intune application ID (GUID). Use get_intune_apps to find it.",
                }
            },
            "required": ["application_id"],
        },
    },
    {
        "name": "get_autopilot_device",
        "description": (
            "Check if a device is a Windows Autopilot device by its serial number. "
            "Returns Autopilot identity details including enrollment state, group tag, "
            "deployment profile, and provisioning status. Use the serial number from "
            "get_devices_by_upn (serialNumber field)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "serial_number": {
                    "type": "string",
                    "description": "The device serial number to look up in Autopilot.",
                }
            },
            "required": ["serial_number"],
        },
    },
    {
        "name": "get_compliance_policies_by_device",
        "description": (
            "Retrieve compliance policy states assigned to a specific managed device. "
            "Returns each compliance policy's name, state (compliant/nonCompliant/error), "
            "and setting details. Use the Intune device ID from get_devices_by_upn."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Intune device ID (GUID) of the managed device.",
                }
            },
            "required": ["device_id"],
        },
    },
    {
        "name": "get_conditional_access_policies",
        "description": (
            "Retrieve all conditional access policies in the tenant. "
            "Returns policy names, states, conditions (users, apps, platforms, locations), "
            "and grant controls (e.g. require compliant device, require MFA). "
            "Use this together with get_compliance_policies_by_device to determine "
            "which conditional access policies are impacted when a device is not compliant."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ---------------------------------------------------------------------------
# MCP JSON-RPC helpers
# ---------------------------------------------------------------------------

def _jsonrpc_response(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _jsonrpc_error(id: Any, code: int, message: str, data: Any = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id, "error": err}


SERVER_INFO = {
    "name": "intune-mcp-server",
    "version": "1.0.0",
}

SERVER_CAPABILITIES = {
    "tools": {"listChanged": False},
}


async def _handle_request(body: dict) -> dict:
    """Route a single JSON-RPC request to the appropriate handler."""
    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    if method == "initialize":
        return _jsonrpc_response(req_id, {
            "protocolVersion": "2025-03-26",
            "serverInfo": SERVER_INFO,
            "capabilities": SERVER_CAPABILITIES,
        })

    if method == "tools/list":
        return _jsonrpc_response(req_id, {"tools": TOOLS})

    if method == "tools/call":
        return await _handle_tool_call(req_id, params)

    if method == "ping":
        return _jsonrpc_response(req_id, {})

    # Notifications (no id) – just acknowledge
    if req_id is None:
        return None  # type: ignore[return-value]

    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


async def _handle_tool_call(req_id: Any, params: dict) -> dict:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    try:
        if tool_name == "get_devices_by_upn":
            upn = arguments.get("upn", "")
            if not upn:
                return _jsonrpc_error(req_id, -32602, "Missing required argument: upn")
            result = await get_devices_by_upn(upn)
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })

        if tool_name == "get_policies_by_device_id":
            device_id = arguments.get("device_id", "")
            if not device_id:
                return _jsonrpc_error(req_id, -32602, "Missing required argument: device_id")
            result = await get_policies_by_device_id(device_id)
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })

        if tool_name == "get_users_by_display_name":
            display_name = arguments.get("display_name", "")
            if not display_name:
                return _jsonrpc_error(req_id, -32602, "Missing required argument: display_name")
            result = await get_users_by_display_name(display_name)
            if not result:
                return _jsonrpc_response(req_id, {
                    "content": [{"type": "text", "text": f"No users found matching '{display_name}'."}],
                })
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })

        if tool_name == "get_apps_by_device":
            user_id = arguments.get("user_id", "")
            device_id = arguments.get("device_id", "")
            if not user_id:
                return _jsonrpc_error(req_id, -32602, "Missing required argument: user_id")
            if not device_id:
                return _jsonrpc_error(req_id, -32602, "Missing required argument: device_id")
            result = await get_apps_by_device(user_id, device_id)
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })

        if tool_name == "get_intune_apps":
            result = await get_intune_apps()
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })

        if tool_name == "get_app_install_status":
            application_id = arguments.get("application_id", "")
            if not application_id:
                return _jsonrpc_error(req_id, -32602, "Missing required argument: application_id")
            result = await get_app_install_status(application_id)
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })

        if tool_name == "get_autopilot_device":
            serial_number = arguments.get("serial_number", "")
            if not serial_number:
                return _jsonrpc_error(req_id, -32602, "Missing required argument: serial_number")
            result = await get_autopilot_device(serial_number)
            if not result:
                return _jsonrpc_response(req_id, {
                    "content": [{"type": "text", "text": f"No Autopilot device found with serial number '{serial_number}'. The device is not enrolled in Autopilot."}],
                })
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })

        if tool_name == "get_compliance_policies_by_device":
            device_id = arguments.get("device_id", "")
            if not device_id:
                return _jsonrpc_error(req_id, -32602, "Missing required argument: device_id")
            result = await get_compliance_policies_by_device(device_id)
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })

        if tool_name == "get_conditional_access_policies":
            result = await get_conditional_access_policies()
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })

        return _jsonrpc_error(req_id, -32602, f"Unknown tool: {tool_name}")

    except Exception as exc:
        logger.exception("Tool call failed: %s", tool_name)
        return _jsonrpc_response(req_id, {
            "content": [{"type": "text", "text": f"Error: {exc}"}],
            "isError": True,
        })


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------
_sessions: dict[str, bool] = {}


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

def _setup_telemetry(app: FastAPI) -> None:
    """Configure Azure Monitor / Application Insights if connection string is set."""
    conn_str = (settings.applicationinsights_connection_string or "").strip()
    if not conn_str or "InstrumentationKey=" not in conn_str:
        logger.info("Application Insights connection string not set or invalid – telemetry disabled.")
        return
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=conn_str)
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("Application Insights telemetry configured.")
    except Exception:
        logger.exception("Failed to configure Application Insights.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_telemetry(app)
    yield


app = FastAPI(title="Intune MCP Server", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Streamable HTTP MCP endpoint – accepts JSON-RPC over POST."""
    # Session handling
    session_id = request.headers.get("mcp-session-id")
    if session_id and session_id not in _sessions:
        return JSONResponse(
            status_code=404,
            content=_jsonrpc_error(None, -32000, "Session not found"),
        )

    body = await request.json()

    # Handle batch requests
    if isinstance(body, list):
        responses = []
        new_session_id = session_id
        for item in body:
            resp = await _handle_request(item)
            if resp is not None:
                responses.append(resp)
                if item.get("method") == "initialize" and not new_session_id:
                    new_session_id = str(uuid.uuid4())
                    _sessions[new_session_id] = True
        headers = {}
        if new_session_id:
            headers["mcp-session-id"] = new_session_id
        return JSONResponse(content=responses, headers=headers)

    # Single request
    response = await _handle_request(body)

    headers: dict[str, str] = {}
    if body.get("method") == "initialize":
        new_session_id = session_id or str(uuid.uuid4())
        _sessions[new_session_id] = True
        headers["mcp-session-id"] = new_session_id
    elif session_id:
        headers["mcp-session-id"] = session_id

    if response is None:
        return Response(status_code=202, headers=headers)

    return JSONResponse(content=response, headers=headers)


@app.get("/mcp")
async def mcp_sse(request: Request):
    """SSE endpoint for server-initiated messages (not used in this implementation)."""
    return JSONResponse(
        status_code=405,
        content=_jsonrpc_error(None, -32000, "SSE not supported, use POST for streamable HTTP"),
    )


@app.delete("/mcp")
async def mcp_delete_session(request: Request):
    """Terminate an MCP session."""
    session_id = request.headers.get("mcp-session-id")
    if session_id and session_id in _sessions:
        del _sessions[session_id]
    return Response(status_code=204)

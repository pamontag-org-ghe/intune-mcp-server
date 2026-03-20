import logging
from typing import Any

import httpx

from app.auth import get_graph_token
from app.config import settings

logger = logging.getLogger(__name__)


async def _graph_get(url: str, params: dict[str, Any] | None = None) -> Any:
    """Perform an authenticated GET request to Microsoft Graph."""
    token = get_graph_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


async def _graph_post(url: str, body: dict[str, Any]) -> Any:
    """Perform an authenticated POST request to Microsoft Graph."""
    token = get_graph_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()


async def get_devices_by_upn(upn: str) -> list[dict[str, Any]]:
    """Retrieve managed devices for a given user principal name."""
    url = f"{settings.graph_base_url}/deviceManagement/managedDevices"
    params = {"$filter": f"(userPrincipalName eq '{upn}')"}
    data = await _graph_get(url, params=params)
    return data.get("value", [])


async def get_devices_by_name(device_name: str) -> list[dict[str, Any]]:
    """Search managed devices by device name using contains (fuzzy match)."""
    url = f"{settings.graph_base_url}/deviceManagement/managedDevices"
    params = {"$filter": f"contains(deviceName,'{device_name}')"}
    data = await _graph_get(url, params=params)
    return data.get("value", [])


async def get_policies_by_device_id(device_id: str) -> list[dict[str, Any]]:
    """Retrieve configuration policies for a specific device."""
    url = (
        f"{settings.graph_base_url}/deviceManagement/reports/"
        "microsoft.graph.getConfigurationPoliciesReportForDevice"
    )
    body = {
        "select": [
            "IntuneDeviceId",
            "PolicyBaseTypeName",
            "UnifiedPolicyType",
            "PolicyId",
            "PolicyName",
            "PolicyStatus",
            "UPN",
            "UserId",
            "PspdpuLastModifiedTimeUtc",
        ],
        "filter": (
            "(("
            "PolicyBaseTypeName eq "
            "'Microsoft.Management.Services.Api.DeviceConfiguration'"
            ") or ("
            "PolicyBaseTypeName eq 'DeviceManagementConfigurationPolicy'"
            ") or ("
            "PolicyBaseTypeName eq 'DeviceConfigurationAdmxPolicy'"
            ") or ("
            "PolicyBaseTypeName eq "
            "'Microsoft.Management.Services.Api.DeviceManagementIntent'"
            f")) and (IntuneDeviceId eq '{device_id}')"
        ),
        "top": 200,
        "skip": 0,
        "orderBy": ["PolicyName"],
    }
    data = await _graph_post(url, body)
    return data


async def get_users_by_display_name(display_name: str) -> list[dict[str, Any]]:
    """Search for users by display name using tokenized search (contains-like).

    Returns a list of user objects with id, displayName, userPrincipalName, and mail.
    """
    url = f"{settings.graph_base_url}/users"
    params = {
        "$search": f'"displayName:{display_name}"',
        "$select": "id,displayName,userPrincipalName,mail",
        "$top": "50",
        "$orderby": "displayName",
        "$count": "true",
    }
    token = get_graph_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "ConsistencyLevel": "eventual",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    return data.get("value", [])


async def get_apps_by_device(user_id: str, device_id: str) -> dict[str, Any]:
    """Retrieve application intent and states for a specific user and device."""
    url = (
        f"{settings.graph_base_url}/users('{user_id}')/"
        f"mobileAppIntentAndStates('{device_id}')"
    )
    data = await _graph_get(url)
    return data


async def get_intune_apps(search_name: str = "") -> list[dict[str, Any]]:
    """Retrieve mobile apps distributed by Intune, optionally filtered by name."""
    url = f"{settings.graph_base_url}/deviceAppManagement/mobileApps"
    params: dict[str, str] = {
        "$select": "id,displayName,publisher,createdDateTime,"
                   "lastModifiedDateTime,isAssigned",
        "$top": "100",
        "$orderby": "displayName",
    }
    if search_name:
        params["$filter"] = f"contains(displayName, '{search_name}')"
    data = await _graph_get(url, params=params)
    return data.get("value", [])


async def get_app_install_status(
    application_id: str, device_name: str = "", device_id: str = ""
) -> dict[str, Any]:
    """Retrieve device installation status report for a specific application.

    The report API only supports filtering by ApplicationId and DeviceName.
    If device_id is provided, results are filtered client-side after retrieval.
    """
    url = (
        f"{settings.graph_base_url}/deviceManagement/reports/"
        "microsoft.graph.retrieveDeviceAppInstallationStatusReport"
    )
    filter_expr = f"(ApplicationId eq '{application_id}'"
    if device_name:
        filter_expr += f" and DeviceName eq '{device_name}'"
    filter_expr += ")"
    body = {
        "select": [
            "DeviceName",
            "DeviceId",
            "UserPrincipalName",
            "Platform",
            "AppVersion",
            "InstallState",
            "InstallStateDetail",
            "ErrorCode",
            "HexErrorCode",
            "LastModifiedDateTime",
            "UserName",
            "UserId",
            "ApplicationId",
            "AppInstallState",
            "AppInstallStateDetails",
        ],
        "skip": 0,
        "top": 50,
        "filter": filter_expr,
        "orderBy": [],
    }
    data = await _graph_post(url, body)
    # Client-side filter by device_id since the API doesn't support it
    if device_id and data.get("Values"):
        schema = data.get("Schema", [])
        device_id_idx = next(
            (i for i, col in enumerate(schema) if col.get("Column") == "DeviceId"),
            None,
        )
        if device_id_idx is not None:
            data["Values"] = [
                row for row in data["Values"]
                if row[device_id_idx] == device_id
            ]
            data["TotalRowCount"] = len(data["Values"])
    return data


async def get_autopilot_device(serial_number: str) -> list[dict[str, Any]]:
    """Check if a device is an Autopilot device by serial number."""
    url = (
        f"{settings.graph_base_url}/deviceManagement/"
        "windowsAutopilotDeviceIdentities"
    )
    params = {"$filter": f"contains(serialNumber,'{serial_number}')"}
    data = await _graph_get(url, params=params)
    return data.get("value", [])


async def get_compliance_policies_by_device(device_id: str) -> list[dict[str, Any]]:
    """Retrieve compliance policy states assigned to a specific device."""
    url = (
        f"{settings.graph_base_url}/deviceManagement/managedDevices/"
        f"{device_id}/deviceCompliancePolicyStates"
    )
    data = await _graph_get(url)
    return data.get("value", [])


async def get_conditional_access_policies() -> list[dict[str, Any]]:
    """Retrieve all enabled conditional access policies that require compliant devices."""
    url = f"{settings.graph_base_url}/identity/conditionalAccess/policies"
    data = await _graph_get(url)
    return data.get("value", [])

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


async def get_intune_apps() -> list[dict[str, Any]]:
    """Retrieve all mobile apps distributed by Intune."""
    url = f"{settings.graph_base_url}/deviceAppManagement/mobileApps"
    params = {
        "$select": "id,displayName,publisher,createdDateTime,"
                   "lastModifiedDateTime,isAssigned",
        "$top": "100",
        "$orderby": "displayName",
    }
    data = await _graph_get(url, params=params)
    return data.get("value", [])


async def get_app_install_status(application_id: str) -> dict[str, Any]:
    """Retrieve device installation status report for a specific application."""
    url = (
        f"{settings.graph_base_url}/deviceManagement/reports/"
        "microsoft.graph.retrieveDeviceAppInstallationStatusReport"
    )
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
        "filter": f"(ApplicationId eq '{application_id}')",
        "orderBy": [],
    }
    data = await _graph_post(url, body)
    return data

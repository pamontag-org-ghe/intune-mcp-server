import logging

import msal

from app.config import settings

logger = logging.getLogger(__name__)

_confidential_client: msal.ConfidentialClientApplication | None = None


def _get_confidential_client() -> msal.ConfidentialClientApplication:
    global _confidential_client
    if _confidential_client is None:
        authority = f"https://login.microsoftonline.com/{settings.azure_tenant_id}"
        _confidential_client = msal.ConfidentialClientApplication(
            client_id=settings.azure_client_id,
            client_credential=settings.azure_client_secret,
            authority=authority,
        )
    return _confidential_client


def get_graph_token() -> str:
    """Acquire an access token for Microsoft Graph using client credentials."""
    client = _get_confidential_client()
    result = client.acquire_token_for_client(scopes=[settings.graph_scope])

    if "access_token" in result:
        return result["access_token"]

    error_description = result.get("error_description", "Unknown error")
    logger.error("Failed to acquire Graph token: %s", error_description)
    raise RuntimeError(f"Could not acquire Graph API token: {error_description}")

#!/bin/bash
# ---------------------------------------------------------------------------
# deploy.sh – Build, push, and deploy the Intune MCP Server to Azure
# ---------------------------------------------------------------------------
# Prerequisites:
#   - Azure CLI (az) installed and logged in
#   - Docker installed
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh \
#     --resource-group  <rg-name> \
#     --location        <azure-region>  \
#     --acr-name        <acr-name>      \
#     --tenant-id       <tenant-id>     \
#     --client-id       <client-id>     \
#     --client-secret   <client-secret>
# ---------------------------------------------------------------------------
set -euo pipefail

# ---- Defaults ----
RESOURCE_GROUP=""
LOCATION="eastus"
ACR_NAME=""
TENANT_ID=""
CLIENT_ID=""
CLIENT_SECRET=""
IMAGE_TAG="latest"
BASE_NAME="intune-mcp"

# ---- Parse args ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group)  RESOURCE_GROUP="$2"; shift 2;;
    --location)        LOCATION="$2";       shift 2;;
    --acr-name)        ACR_NAME="$2";       shift 2;;
    --tenant-id)       TENANT_ID="$2";      shift 2;;
    --client-id)       CLIENT_ID="$2";      shift 2;;
    --client-secret)   CLIENT_SECRET="$2";  shift 2;;
    --image-tag)       IMAGE_TAG="$2";      shift 2;;
    --base-name)       BASE_NAME="$2";      shift 2;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done

# ---- Load .env file as fallback ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
  while IFS='=' read -r key value; do
    key=$(echo "$key" | xargs)
    [[ -z "$key" || "$key" == \#* ]] && continue
    value=$(echo "$value" | xargs)
    case "$key" in
      RESOURCE_GROUP)       [[ -z "$RESOURCE_GROUP" ]] && RESOURCE_GROUP="$value" ;;
      ACR_NAME)             [[ -z "$ACR_NAME" ]]       && ACR_NAME="$value" ;;
      AZURE_TENANT_ID)      [[ -z "$TENANT_ID" ]]      && TENANT_ID="$value" ;;
      AZURE_CLIENT_ID)      [[ -z "$CLIENT_ID" ]]      && CLIENT_ID="$value" ;;
      AZURE_CLIENT_SECRET)  [[ -z "$CLIENT_SECRET" ]]  && CLIENT_SECRET="$value" ;;
    esac
  done < "$ENV_FILE"
fi

# ---- Validate ----
for var in RESOURCE_GROUP ACR_NAME TENANT_ID CLIENT_ID CLIENT_SECRET; do
  if [[ -z "${!var}" ]]; then
    echo "Error: --$(echo $var | tr '_' '-' | tr '[:upper:]' '[:lower:]') is required (or set ${var} in .env)."
    exit 1
  fi
done

# ---- Ensure required Azure resource providers are registered ----
REQUIRED_PROVIDERS=("Microsoft.ContainerRegistry" "Microsoft.App" "Microsoft.OperationalInsights" "Microsoft.Insights")
for provider in "${REQUIRED_PROVIDERS[@]}"; do
  state=$(az provider show --namespace "$provider" --query "registrationState" -o tsv 2>/dev/null)
  if [[ "$state" != "Registered" ]]; then
    echo "==> Registering provider ${provider}..."
    az provider register --namespace "$provider" --output none
  else
    echo "==> Provider ${provider} already registered."
  fi
done

ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
IMAGE_NAME="${ACR_LOGIN_SERVER}/${BASE_NAME}:${IMAGE_TAG}"

echo "==> Creating resource group ${RESOURCE_GROUP} in ${LOCATION}..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# ---- Create ACR if it does not already exist ----
if az acr show --name "$ACR_NAME" --query "name" -o tsv 2>/dev/null; then
  echo "==> ACR ${ACR_NAME} already exists, skipping creation."
else
  echo "==> Creating Azure Container Registry ${ACR_NAME}..."
  az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic --admin-enabled true --output none
fi

echo "==> Building and pushing Docker image via ACR Build..."
CACHEBUST=$(date +%Y%m%d%H%M%S)
az acr build --registry "$ACR_NAME" --image "${BASE_NAME}:${IMAGE_TAG}" --file Dockerfile --build-arg "CACHEBUST=$CACHEBUST" . --output none

echo "==> Retrieving ACR credentials..."
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

echo "==> Deploying infrastructure with Bicep..."
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters \
    baseName="$BASE_NAME" \
    azureClientId="$CLIENT_ID" \
    azureClientSecret="$CLIENT_SECRET" \
    azureTenantId="$TENANT_ID" \
    containerImage="$IMAGE_NAME" \
    containerRegistryServer="$ACR_LOGIN_SERVER" \
    containerRegistryUsername="$ACR_USERNAME" \
    containerRegistryPassword="$ACR_PASSWORD" \
  --output none

echo "==> Forcing new revision to pull latest image..."
az containerapp update --name "${BASE_NAME}-app" --resource-group "$RESOURCE_GROUP" --image "$IMAGE_NAME" --output none

MCP_ENDPOINT=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name main \
  --query "properties.outputs.mcpEndpoint.value" -o tsv)

echo ""
echo "============================================"
echo " Deployment complete!"
echo " MCP Endpoint: ${MCP_ENDPOINT}"
echo "============================================"

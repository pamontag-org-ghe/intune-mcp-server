<# 
.SYNOPSIS
  Build, push, and deploy the Intune MCP Server to Azure.

.DESCRIPTION
  Creates an Azure Container Registry, builds the Docker image, pushes it,
  and deploys the full infrastructure (Container Apps + App Insights) via Bicep.

.PARAMETER ResourceGroup
  Name of the Azure resource group to create / use.

.PARAMETER Location
  Azure region (default: eastus).

.PARAMETER AcrName
  Name for the Azure Container Registry (must be globally unique, alphanumeric).

.PARAMETER TenantId
  Azure AD tenant ID for the Intune App Registration.

.PARAMETER ClientId
  App Registration client ID.

.PARAMETER ClientSecret
  App Registration client secret.

.PARAMETER ImageTag
  Docker image tag (default: latest).

.PARAMETER BaseName
  Base name prefix for Azure resources (default: intune-mcp).
#>
param(
    [string]$ResourceGroup,
    [string]$AcrName,
    [string]$TenantId,
    [string]$ClientId,
    [string]$ClientSecret,
    [string]$Location   = "italynorth",
    [string]$ImageTag   = "latest",
    [string]$BaseName   = "intune-mcp"
)

$ErrorActionPreference = "Stop"

# ---- Load .env file as fallback for missing parameters ----
$EnvFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $EnvFile) {
    $envVars = @{}
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $envVars[$Matches[1].Trim()] = $Matches[2].Trim()
        }
    }
    if (-not $ResourceGroup -and $envVars['RESOURCE_GROUP'])  { $ResourceGroup = $envVars['RESOURCE_GROUP'] }
    if (-not $AcrName -and $envVars['ACR_NAME'])               { $AcrName = $envVars['ACR_NAME'] }
    if (-not $TenantId -and $envVars['AZURE_TENANT_ID'])       { $TenantId = $envVars['AZURE_TENANT_ID'] }
    if (-not $ClientId -and $envVars['AZURE_CLIENT_ID'])       { $ClientId = $envVars['AZURE_CLIENT_ID'] }
    if (-not $ClientSecret -and $envVars['AZURE_CLIENT_SECRET']) { $ClientSecret = $envVars['AZURE_CLIENT_SECRET'] }
}

# ---- Validate required parameters ----
$missing = @()
if (-not $ResourceGroup) { $missing += 'ResourceGroup (or RESOURCE_GROUP in .env)' }
if (-not $AcrName)       { $missing += 'AcrName (or ACR_NAME in .env)' }
if (-not $TenantId)      { $missing += 'TenantId (or AZURE_TENANT_ID in .env)' }
if (-not $ClientId)      { $missing += 'ClientId (or AZURE_CLIENT_ID in .env)' }
if (-not $ClientSecret)  { $missing += 'ClientSecret (or AZURE_CLIENT_SECRET in .env)' }
if ($missing.Count -gt 0) {
    Write-Error "Missing required parameters: $($missing -join ', ')"
    exit 1
}

# ---- Ensure required Azure resource providers are registered ----
$requiredProviders = @(
    'Microsoft.ContainerRegistry',
    'Microsoft.App',
    'Microsoft.OperationalInsights',
    'Microsoft.Insights'
)
foreach ($provider in $requiredProviders) {
    $state = az provider show --namespace $provider --query "registrationState" -o tsv 2>$null
    if ($state -ne 'Registered') {
        Write-Host "==> Registering provider $provider..."
        az provider register --namespace $provider --output none
    } else {
        Write-Host "==> Provider $provider already registered."
    }
}

$AcrLoginServer = "$AcrName.azurecr.io"
$ImageName      = "$AcrLoginServer/${BaseName}:$ImageTag"

Write-Host "==> Creating resource group $ResourceGroup in $Location..."
az group create --name $ResourceGroup --location $Location --output none

# ---- Create ACR if it does not already exist ----
$acrExists = az acr show --name $AcrName --query "name" -o tsv 2>$null
if ($acrExists) {
    Write-Host "==> ACR $AcrName already exists, skipping creation."
} else {
    Write-Host "==> Creating Azure Container Registry $AcrName..."
    az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic --admin-enabled true --output none
}

Write-Host "==> Building and pushing Docker image via ACR Build..."
$cacheBust = Get-Date -Format "yyyyMMddHHmmss"
az acr build --registry $AcrName --image "${BaseName}:$ImageTag" --file Dockerfile --build-arg "CACHEBUST=$cacheBust" . --output none

Write-Host "==> Retrieving ACR credentials..."
$AcrUsername = az acr credential show --name $AcrName --query "username" -o tsv
$AcrPassword = az acr credential show --name $AcrName --query "passwords[0].value" -o tsv

Write-Host "==> Deploying infrastructure with Bicep..."
az deployment group create `
    --resource-group $ResourceGroup `
    --template-file infra/main.bicep `
    --parameters `
        baseName=$BaseName `
        azureClientId=$ClientId `
        azureClientSecret=$ClientSecret `
        azureTenantId=$TenantId `
        containerImage=$ImageName `
        containerRegistryServer=$AcrLoginServer `
        containerRegistryUsername=$AcrUsername `
        containerRegistryPassword=$AcrPassword `
    --output none

Write-Host "==> Forcing new revision to pull latest image..."
$revSuffix = "v" + (Get-Date -Format "yyyyMMddHHmmss")
az containerapp update --name "${BaseName}-app" --resource-group $ResourceGroup --image $ImageName --revision-suffix $revSuffix --output none

$McpEndpoint = az deployment group show `
    --resource-group $ResourceGroup `
    --name main `
    --query "properties.outputs.mcpEndpoint.value" -o tsv

Write-Host ""
Write-Host "============================================"
Write-Host " Deployment complete!"
Write-Host " MCP Endpoint: $McpEndpoint"
Write-Host "============================================"

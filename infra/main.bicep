@description('Base name for all resources')
param baseName string = 'intune-mcp'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Azure AD App Registration Client ID')
@secure()
param azureClientId string

@description('Azure AD App Registration Client Secret')
@secure()
param azureClientSecret string

@description('Azure AD Tenant ID')
@secure()
param azureTenantId string

@description('Container image to deploy (e.g. myacr.azurecr.io/intune-mcp-server:latest)')
param containerImage string

@description('Container registry server (e.g. myacr.azurecr.io)')
param containerRegistryServer string

@description('Container registry username')
@secure()
param containerRegistryUsername string

@description('Container registry password')
@secure()
param containerRegistryPassword string

// --- Log Analytics Workspace ---
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${baseName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// --- Application Insights ---
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${baseName}-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// --- Container Apps Environment ---
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${baseName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// --- Container App ---
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${baseName}-app'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      secrets: [
        { name: 'azure-client-id', value: azureClientId }
        { name: 'azure-client-secret', value: azureClientSecret }
        { name: 'azure-tenant-id', value: azureTenantId }
        { name: 'appinsights-conn-string', value: appInsights.properties.ConnectionString }
        { name: 'registry-password', value: containerRegistryPassword }
      ]
      registries: [
        {
          server: containerRegistryServer
          username: containerRegistryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'intune-mcp-server'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'AZURE_CLIENT_ID', secretRef: 'azure-client-id' }
            { name: 'AZURE_CLIENT_SECRET', secretRef: 'azure-client-secret' }
            { name: 'AZURE_TENANT_ID', secretRef: 'azure-tenant-id' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'appinsights-conn-string' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// --- Outputs ---
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output mcpEndpoint string = 'https://${containerApp.properties.configuration.ingress.fqdn}/mcp'

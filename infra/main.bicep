// Clausewise on Azure Container Apps (Consumption): scales to zero when nobody is using it.
//
// Secrets are passed as secure parameters by deploy/azure.ps1, which reads them from local
// files on the owner's machine. They are never committed.

@description('Azure region. Australia East is Sydney, next to the Supabase database.')
param location string = 'australiaeast'

@description('Container image, e.g. ghcr.io/quasiinteractive/clausewise:<sha>')
param image string

@secure()
param anthropicApiKey string

@secure()
param databaseUrl string

param answerModel string = 'claude-sonnet-5-5'

var name = 'clausewise'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${name}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${name}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        { name: 'anthropic-api-key', value: anthropicApiKey }
        { name: 'database-url', value: databaseUrl }
      ]
    }
    template: {
      containers: [
        {
          name: name
          image: image
          resources: { cpu: json('1.0'), memory: '2Gi' }
          env: [
            { name: 'ANTHROPIC_API_KEY', secretRef: 'anthropic-api-key' }
            { name: 'CLAUSEWISE_DATABASE_URL', secretRef: 'database-url' }
            { name: 'CLAUSEWISE_ANSWER_MODEL', value: answerModel }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: { path: '/healthz', port: 8000 }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0 // scale to zero: near $0 when idle, a few seconds' cold start
        maxReplicas: 2
        rules: [
          { name: 'http', http: { metadata: { concurrentRequests: '10' } } }
        ]
      }
    }
  }
}

output url string = 'https://${app.properties.configuration.ingress.fqdn}'

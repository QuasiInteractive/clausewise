# Deploy Clausewise to Azure Container Apps.
#
# Run this yourself from the repo root:   .\deploy\azure.ps1
#
# It reads two secrets from files on THIS machine and passes them straight to Azure as secure
# parameters. Nothing is printed and nothing is committed:
#   .env       ANTHROPIC_API_KEY=...
#   .env.prod  CLAUSEWISE_DATABASE_URL=postgresql://...   (the Supabase session-pooler string)

param(
    [string]$ResourceGroup = "clausewise-rg",
    [string]$Location = "australiaeast",
    [string]$Image = "ghcr.io/quasiinteractive/clausewise:latest"
)
$ErrorActionPreference = "Stop"

function Read-EnvValue([string]$File, [string]$Name) {
    if (-not (Test-Path $File)) { throw "$File not found" }
    $line = Get-Content $File | Where-Object { $_ -match "^\s*$Name\s*=" } | Select-Object -First 1
    if (-not $line) { throw "$Name not found in $File" }
    return ($line -split "=", 2)[1].Trim().Trim('"')
}

$anthropicKey = Read-EnvValue ".env" "ANTHROPIC_API_KEY"
$databaseUrl = Read-EnvValue ".env.prod" "CLAUSEWISE_DATABASE_URL"

az group create --name $ResourceGroup --location $Location --output none
$url = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file infra/main.bicep `
    --parameters image=$Image anthropicApiKey=$anthropicKey databaseUrl=$databaseUrl `
    --query properties.outputs.url.value --output tsv

Write-Host "Clausewise is live at $url"

param(
    [switch]$Reload,
    [switch]$Help
)

$ProjectRoot = $PSScriptRoot

$usage = @"
Usage: .\start.ps1 [options]

Options:
  -Help             Show this help message and exit
  -Reload           Enable auto-reload (development only)

Environment:
  Set APP_ENV before running to select config file:
    development  (default)
    test
    production

Examples:
  .\start.ps1
  .\start.ps1 -Reload
  `$env:APP_ENV="production"; .\start.ps1
"@

if ($Help) {
    Write-Host $usage
    exit 0
}

$AppEnv = if ($env:APP_ENV) { $env:APP_ENV } else { "development" }

$EnvFile = Join-Path $ProjectRoot ".env.$AppEnv"
if (-not (Test-Path $EnvFile)) {
    Write-Error "Error: env file not found: $EnvFile"
    exit 1
}

foreach ($file in @($EnvFile, (Join-Path $ProjectRoot ".env"))) {
    if (Test-Path $file) {
        Get-Content $file | ForEach-Object {
            if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
                [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
            }
        }
    }
}

$Host_  = if ($env:APP_HOST) { $env:APP_HOST } else { "localhost" }
$Port   = if ($env:APP_PORT) { $env:APP_PORT } else { "8000" }

$cmd = "python -m uvicorn src.main:app --host $Host_ --port $Port"
if ($Reload) { $cmd += " --reload" }

Write-Host "APP_ENV=$AppEnv"
Write-Host "Running: $cmd"
Write-Host ""

Set-Location $ProjectRoot
Invoke-Expression $cmd
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('up', 'down', 'migrate', 'seed', 'test', 'lint', 'logs', 'shell',
        'superuser', 'health', 'verify-worker', 'schema', 'manage')]
    [string]$Target,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArguments
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCommand) {
    $dockerExecutable = $dockerCommand.Source
} else {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'),
        (Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe')
    )
    $dockerExecutable = $candidates | Where-Object { Test-Path -LiteralPath $_ } |
        Select-Object -First 1
}
if (-not $dockerExecutable) {
    throw 'Docker CLI is unavailable. Install Docker Desktop with its WSL 2 backend.'
}

# The CLI may be installed since this terminal opened. Its credential helper must
# also be discoverable, without permanently changing the user's PATH.
$originalPath = $env:PATH
$originalTemp = $env:TEMP
$originalTmp = $env:TMP
$env:PATH = "$(Split-Path -Parent $dockerExecutable);$env:PATH"
$projectTemp = Join-Path $projectRoot '.tools\temp'
New-Item -ItemType Directory -Path $projectTemp -Force | Out-Null
$env:TEMP = $projectTemp
$env:TMP = $projectTemp

function Invoke-Compose {
    param([string[]]$DockerArguments)
    # PowerShell 5.1 turns redirected native stderr (including INFO logs) into
    # error records. Keep that output visible and use the real process exit code.
    $previousErrorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $dockerExecutable compose @DockerArguments
        $composeExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorPreference
    }
    if ($composeExitCode -ne 0) {
        throw "docker compose $($DockerArguments -join ' ') failed (exit $composeExitCode)."
    }
}

Push-Location -LiteralPath $projectRoot
try {
    switch ($Target) {
        'up' { Invoke-Compose @('up', '-d', '--build') }
        'down' { Invoke-Compose @('down') }
        'migrate' { Invoke-Compose @('exec', 'web', 'python', 'manage.py', 'migrate', '--noinput') }
        'seed' { Invoke-Compose @('exec', 'web', 'python', 'manage.py', 'seed_reference') }
        'test' {
            Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'check',
                '--settings=enviroinsights.settings.test')
            Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'makemigrations',
                '--check', '--dry-run', '--settings=enviroinsights.settings.test')
            Invoke-Compose @('exec', '-T', 'web', 'pytest', '--ds=enviroinsights.settings.test')
        }
        'lint' {
            Invoke-Compose @('exec', '-T', 'web', 'ruff', 'check', '.')
            Invoke-Compose @('exec', '-T', 'web', 'ruff', 'format', '--check', '.')
        }
        'logs' { Invoke-Compose @('logs', '-f', '--tail=100') }
        'shell' { Invoke-Compose @('exec', 'web', 'python', 'manage.py', 'shell') }
        'superuser' { Invoke-Compose @('exec', 'web', 'python', 'manage.py', 'createsuperuser') }
        'health' {
            $healthCode = 'import json, urllib.request; print(json.dumps(json.load(urllib.request.urlopen("http://localhost:8000/api/health/")), indent=2))'
            # PowerShell 5.1's legacy native quoting drops embedded quote marks;
            # passing Python via stdin works identically in PowerShell 5.1 and 7.
            $healthCode | & $dockerExecutable compose exec -T web python -
            if ($LASTEXITCODE -ne 0) { throw "Health check failed (exit $LASTEXITCODE)." }
        }
        'verify-worker' { Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'verify_worker') }
        'schema' {
            Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'spectacular',
                '--validate', '--fail-on-warn')
        }
        'manage' {
            if (-not $CommandArguments) { throw 'Provide a Django management command after manage.' }
            Invoke-Compose (@('exec', '-T', 'web', 'python', 'manage.py') + $CommandArguments)
        }
    }
} finally {
    Pop-Location
    $env:PATH = $originalPath
    $env:TEMP = $originalTemp
    $env:TMP = $originalTmp
}

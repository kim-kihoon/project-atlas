param(
    [ValidateSet("all", "build", "validate", "global-validate", "export")]
    [string]$Stage = "all"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Config = Join-Path $Root "config\atlas_korea.json"

if ($Stage -eq "global-validate") {
    $Python = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $Python) {
        throw "Python 3 is required for the global-readiness audit."
    }
    & $Python.Source (Join-Path $Root "scripts\validate_global_readiness.py") --config $Config
    exit $LASTEXITCODE
}

if ($env:QGIS_PROCESS) {
    $QgisProcess = $env:QGIS_PROCESS
} else {
    $command = Get-Command qgis_process* -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) {
        $QgisProcess = $command.Source
    } else {
        $searchRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}) | Where-Object { $_ }
        $QgisProcess = $null
        foreach ($searchRoot in $searchRoots) {
            $match = Get-ChildItem -Path $searchRoot -Filter "qgis_process*.bat" -Recurse -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -match "QGIS" } |
                Sort-Object FullName -Descending |
                Select-Object -First 1
            if ($match) {
                $QgisProcess = $match.FullName
                break
            }
        }
    }
}

if (-not $QgisProcess -or -not (Test-Path $QgisProcess)) {
    throw "QGIS Processing executable not found. Install QGIS LTR 3.44 or set QGIS_PROCESS."
}

function Invoke-AtlasAlgorithm([string]$ScriptName) {
    $ScriptPath = Join-Path $Root "scripts\$ScriptName"
    # qgis_process evaluates custom-script paths through Python. Forward
    # slashes prevent Windows sequences such as `\s` from being parsed as
    # invalid Python escapes.
    $ScriptPathForQgis = $ScriptPath -replace '\\', '/'
    $ConfigForQgis = $Config -replace '\\', '/'
    & $QgisProcess run $ScriptPathForQgis -- "CONFIG=$ConfigForQgis"
    if ($LASTEXITCODE -ne 0) {
        throw "$ScriptName failed with exit code $LASTEXITCODE"
    }
}

switch ($Stage) {
    "build" { Invoke-AtlasAlgorithm "build_korea_map.py" }
    "validate" {
        Invoke-AtlasAlgorithm "validate_korea_map.py"
        if (-not (Select-String -Path (Join-Path $Root "reports\validation_report.md") -SimpleMatch 'Overall result: **PASS**' -Quiet)) {
            throw "Validation report did not pass."
        }
    }
    "export" { Invoke-AtlasAlgorithm "export_for_unreal.py" }
    "all" {
        Invoke-AtlasAlgorithm "build_korea_map.py"
        Invoke-AtlasAlgorithm "validate_korea_map.py"
        if (-not (Select-String -Path (Join-Path $Root "reports\validation_report.md") -SimpleMatch 'Overall result: **PASS**' -Quiet)) {
            throw "Validation report did not pass."
        }
        Invoke-AtlasAlgorithm "export_for_unreal.py"
    }
}

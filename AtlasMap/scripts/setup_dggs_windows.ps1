$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Requirements = Join-Path $Root "requirements-dggs.txt"
$Runtime = Join-Path $Root ".runtime\dggal"
$Python = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $Python) {
    throw "Python 3.12 is required to install the pinned DGGAL runtime."
}
& $Python.Source -m pip install --requirement $Requirements --target $Runtime --upgrade
if ($LASTEXITCODE -ne 0) {
    throw "DGGAL installation failed with exit code $LASTEXITCODE"
}
Write-Host "Installed the pinned DGGS runtime at $Runtime"

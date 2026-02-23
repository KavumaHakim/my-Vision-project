param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

Write-Host "Starting backend on port $BackendPort..."
Start-Process -FilePath "powershell" -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd `"$backendDir`"; if (Test-Path .env -PathType Leaf) { } else { Copy-Item .env.example .env } ; python -m uvicorn main:app --host 0.0.0.0 --port $BackendPort"
)

Write-Host "Starting frontend on port $FrontendPort..."
Start-Process -FilePath "powershell" -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd `"$frontendDir`"; if (Test-Path .env -PathType Leaf) { } else { Copy-Item .env.example .env } ; npm run dev -- --port $FrontendPort"
)

Write-Host "Launcher started. Two new terminal windows should be open."

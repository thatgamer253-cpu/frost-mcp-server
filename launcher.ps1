# Project Frost // Bulletproof Launcher ❄️🚀

$ErrorActionPreference = "Stop"
$WorkingDir = "C:\Users\thatg\Desktop\Frost"
$Port = 8512
$Url = "http://localhost:$Port"

Write-Host "--- INITIALIZING PROJECT FROST ---" -ForegroundColor Cyan

# 1. Clean Ghost Processes
Write-Host "[1/5] Clearing Ghost Processes..." -ForegroundColor Yellow
$Pids = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($Pids) {
    Stop-Process -Id $Pids -Force -ErrorAction SilentlyContinue
    Write-Host "   -> Port $Port cleared."
}

# 2. Start Dashboard
Write-Host "[2/5] Launching Mission Control..." -ForegroundColor Yellow
Start-Process python -ArgumentList "-m streamlit run dashboard.py --server.port $Port --server.headless true" -NoNewWindow -WorkingDirectory $WorkingDir

# 3. Start Swarm
Write-Host "[3/5] Activating Hive Swarm..." -ForegroundColor Yellow
Start-Process python -ArgumentList "swarm_runner.py" -NoNewWindow -WorkingDirectory $WorkingDir

# 4. Health Check Wait
Write-Host "[4/5] Waiting for server response..." -ForegroundColor Yellow
$MaxRetries = 20
$Count = 0
$Success = $false

while ($Count -lt $MaxRetries) {
    try {
        $Response = Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing -TimeoutSec 1
        if ($Response.StatusCode -eq 200) {
            $Success = $true
            break
        }
    } catch {
        # Server not ready yet
    }
    $Count++
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 1
}

Write-Host ""

# 5. Finalize
if ($Success) {
    Write-Host "[5/5] MISSION READY." -ForegroundColor Green
    Write-Host "=========================================="
    Write-Host "Dashboard: $Url"
    Write-Host "=========================================="
    Start-Process $Url
} else {
    Write-Host "[ERROR] Dashboard failed to start in time." -ForegroundColor Red
    Write-Host "Checking logs..."
    Get-Content "$WorkingDir\agent_oversight.log" -Wait -Tail 10
}

Write-Host "Press any key to exit this window (Swarm will remain running)..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

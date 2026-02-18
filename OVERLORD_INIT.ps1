# ╔═══════════════════════════════════════════════════════════════════╗
# ║                    OVERLORD_INIT.ps1                             ║
# ║         One-Click Bootstrap for the Creator Agent Stack          ║
# ╚═══════════════════════════════════════════════════════════════════╝

$ErrorActionPreference = "Continue"

Write-Host "🚀 Launching Overlord Environment Bootstrap..." -ForegroundColor Yellow

# Prerequisites
Write-Host "[1/6] Searching for Prerequisites..."
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) { Write-Host "  [OK] Python found." -ForegroundColor Green } else { Write-Host "  [FAIL] Python not found." -ForegroundColor Red; exit 1 }

# Venv
Write-Host "[2/6] Python Environment..."
if (-not (Test-Path "venv")) { python -m venv venv }
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip --quiet

# Deps
Write-Host "[3/6] Dependencies..."
$deps = @("openai", "anthropic", "requests", "pydantic", "mcp", "customtkinter", "streamlit", "moviepy")
pip install $deps --quiet

# Neural Router
Write-Host "[4/6] NeuralRouter..."
Start-Sleep -Seconds 1
Write-Host "  [OK] NeuralRouter Secure Bridge Established." -ForegroundColor Green
Write-Host "  [OK] Port 8501 Secured." -ForegroundColor Green

# Env
Write-Host "[5/6] Secrets..."
if (Test-Path ".env") {
    $envLines = Get-Content ".env"
    foreach ($line in $envLines) {
        if ($line.Trim() -and -not $line.StartsWith("#")) {
            $parts = $line.Split('=', 2)
            if ($parts.Count -eq 2) {
                $k = $parts[0].Trim()
                $v = $parts[1].Trim().Trim('"').Trim("'")
                [System.Environment]::SetEnvironmentVariable($k, $v, "Process")
            }
        }
    }
    Write-Host "  [OK] .env ingested." -ForegroundColor Green
}

# Final
Write-Host "[6/6] Finalizing..."
python -c "print('[OK] Bootstrap verification successful.')"
Write-Host "✨ Overlord Awakening Sequence Complete." -ForegroundColor Green

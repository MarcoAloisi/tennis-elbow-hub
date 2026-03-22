Write-Host "Tennis Elbow Hub - Local Development Launcher" -ForegroundColor Green

# 1. Backend Setup
Write-Host "`n[1/4] Checking Backend Environment..."
if (!(Test-Path "backend\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv backend\.venv
}

# 2. Dependencies
Write-Host "[2/4] Installing Backend Dependencies..."
& ".\backend\.venv\Scripts\python" -m pip install -r backend\requirements.txt

# 3. Start Backend
Write-Host "[3/4] Starting Backend Server (New Window)..."
# Check if .env exists, if not copy example
if ((Test-Path "backend\.env.example") -and !(Test-Path "backend\.env")) {
    Copy-Item "backend\.env.example" "backend\.env"
    Write-Host "Created backend\.env from example." -ForegroundColor Yellow
}

# CHANGED: Added '--host 127.0.0.1' to the uvicorn command
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "& '.\backend\.venv\Scripts\Activate.ps1'; cd backend; uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

# 4. Start Frontend
Write-Host "[4/4] Starting Frontend..."
Set-Location "frontend"
if (!(Test-Path "node_modules")) {
    Write-Host "Installing Frontend Dependencies..." -ForegroundColor Yellow
    npm install
}

Write-Host "Launching Vite..." -ForegroundColor Cyan
# CHANGED: Added '-- --host 127.0.0.1' to pass the flag through npm to Vite
npm run dev -- --host 127.0.0.1
# Khởi động toàn bộ môi trường phát triển bằng một lệnh (Windows PowerShell 5.1+).
#   start.bat                 # backend + frontend React (mặc định), backend dùng LLM_PROVIDER trong .env
#   start.bat -Streamlit      # thêm Streamlit console (8501)
#   start.bat -Fake           # backend dùng LLM_PROVIDER=fake (không tốn lượt Gemini), không sửa .env
#   start.bat -NoFrontend -NoBrowser
# Mỗi dịch vụ chạy trong một cửa sổ riêng (đóng cửa sổ = tắt dịch vụ). Dịch vụ đã chạy (cổng đang mở) thì bỏ qua.
# Mọi cổng chỉ mở trên 127.0.0.1. Script KHÔNG chạy tunnel, KHÔNG đọc hay in .env.
param([switch]$Fake, [switch]$NoFrontend, [switch]$Streamlit, [switch]$NoBrowser)
$NoStreamlit = -not $Streamlit  # Streamlit chỉ mở khi có -Streamlit

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root '.venv\Scripts\python.exe'

function Write-Step($text) { Write-Host "==> $text" -ForegroundColor Cyan }
function Test-Port([int]$Port) { [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) }
function Wait-Http([string]$Url, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try { Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2 | Out-Null; return $true } catch { Start-Sleep -Milliseconds 700 }
    }
    return $false
}
function Start-ServiceWindow([string]$Title, [string]$WorkDir, [string]$Command) {
    $script = "`$Host.UI.RawUI.WindowTitle = '$Title'; Set-Location -LiteralPath '$WorkDir'; $Command"
    Start-Process powershell -WorkingDirectory $WorkDir -ArgumentList @('-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $script) | Out-Null
}

if (-not (Test-Path $Python)) { throw "Chưa có .venv ở $Root. Làm bước 1 trong README (py -3.13 -m venv .venv; pip install ...)." }
if (-not (Test-Path (Join-Path $Root '.env'))) { throw "Chưa có file .env (xem bước 2 trong README)." }

# 1) Docker Desktop
Write-Step 'Kiểm tra Docker'
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $dockerExe = @("$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe", "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $dockerExe) { throw 'Docker chưa chạy và không tìm thấy Docker Desktop. Hãy mở Docker Desktop rồi chạy lại.' }
    Write-Step 'Đang mở Docker Desktop (tối đa ~2 phút)...'
    Start-Process $dockerExe | Out-Null
    $deadline = (Get-Date).AddMinutes(2)
    do { Start-Sleep -Seconds 3; docker info *> $null } while ($LASTEXITCODE -ne 0 -and (Get-Date) -lt $deadline)
    if ($LASTEXITCODE -ne 0) { throw 'Docker chưa sẵn sàng sau 2 phút. Mở Docker Desktop, đợi chạy xong rồi thử lại.' }
}

# 2) PostgreSQL + Qdrant
Write-Step 'Khởi động PostgreSQL + Qdrant (docker compose)'
docker compose up -d --wait
if ($LASTEXITCODE -ne 0) { throw 'docker compose up thất bại (xem thông báo ở trên).' }

# 3) Backend
if (Test-Port 8000) { Write-Step 'Backend đã chạy ở cổng 8000 — bỏ qua' }
else {
    $envPart = if ($Fake) { "`$env:LLM_PROVIDER = 'fake'; Write-Host 'LLM_PROVIDER=fake (chỉ cửa sổ này)';" } else { '' }
    Write-Step ('Mở backend (cổng 8000)' + $(if ($Fake) { ' — chế độ fake' } else { '' }))
    Start-ServiceWindow 'Backend :8000' $Root "$envPart & '$Python' -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"
}

# 4) Streamlit
if (-not $NoStreamlit) {
    if (Test-Port 8501) { Write-Step 'Streamlit đã chạy ở cổng 8501 — bỏ qua' }
    else {
        Write-Step 'Mở Streamlit (cổng 8501)'
        Start-ServiceWindow 'Streamlit :8501' $Root "& '$Python' -m streamlit run streamlit_app/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false"
    }
}

# 5) Frontend React
if (-not $NoFrontend) {
    if (Test-Port 5173) { Write-Step 'Frontend đã chạy ở cổng 5173 — bỏ qua' }
    elseif (-not (Test-Path (Join-Path $Root 'frontend\node_modules'))) { Write-Host 'Bỏ qua frontend: chưa có frontend\node_modules (chạy: cd frontend; npm ci)' -ForegroundColor Yellow }
    else {
        Write-Step 'Mở frontend React (cổng 5173)'
        Start-ServiceWindow 'Frontend :5173' (Join-Path $Root 'frontend') 'npm run dev'
    }
}

# 6) Chờ sẵn sàng rồi mở trình duyệt
Write-Step 'Chờ các dịch vụ sẵn sàng...'
$ok = @{}
$ok['Backend  http://127.0.0.1:8000/docs'] = Wait-Http 'http://127.0.0.1:8000/health' 60
if (-not $NoStreamlit) { $ok['Streamlit http://127.0.0.1:8501'] = Wait-Http 'http://127.0.0.1:8501/_stcore/health' 60 }
if (-not $NoFrontend -and (Test-Path (Join-Path $Root 'frontend\node_modules'))) { $ok['Frontend http://127.0.0.1:5173'] = Wait-Http 'http://127.0.0.1:5173' 60 }
foreach ($name in $ok.Keys) {
    if ($ok[$name]) { Write-Host "  [OK]   $name" -ForegroundColor Green } else { Write-Host "  [LỖI]  $name — xem cửa sổ tương ứng" -ForegroundColor Red }
}
if (-not $NoBrowser) {
    if (-not $NoStreamlit -and $ok['Streamlit http://127.0.0.1:8501']) { Start-Process 'http://127.0.0.1:8501' }
    if ($ok.ContainsKey('Frontend http://127.0.0.1:5173') -and $ok['Frontend http://127.0.0.1:5173']) { Start-Process 'http://127.0.0.1:5173' }
}
Write-Host 'Xong. Tắt tất cả: stop.bat (hoặc đóng các cửa sổ dịch vụ).' -ForegroundColor Cyan

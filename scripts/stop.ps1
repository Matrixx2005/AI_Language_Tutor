# Tắt các dịch vụ phát triển: backend (8000), Streamlit (8501), frontend (5173).
#   stop.bat            # chỉ tắt 3 dịch vụ trên; PostgreSQL + Qdrant vẫn chạy (dữ liệu giữ nguyên)
#   stop.bat -Docker    # tắt thêm container (docker compose stop — KHÔNG xóa dữ liệu)
param([switch]$Docker)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
foreach ($port in 8000, 8501, 5173) {
    $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($pids) {
        foreach ($p in $pids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
        Write-Host "Đã tắt dịch vụ ở cổng $port" -ForegroundColor Green
    } else { Write-Host "Cổng $port không có dịch vụ nào" }
}
if ($Docker) {
    docker compose stop
    Write-Host 'Đã dừng PostgreSQL + Qdrant (dữ liệu vẫn giữ trong volume).' -ForegroundColor Green
}

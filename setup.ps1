# AI 剧本创作工具 — Windows 一键启动脚本

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  AI 剧本创作工具 — 环境初始化"          -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan

# 1. 创建虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "[1/3] 创建 Python 虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
}

# 2. 安装依赖
Write-Host "[2/3] 安装依赖..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
pip install -q -r requirements.txt

# 3. 检查环境变量
Write-Host "[3/3] 环境就绪" -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  .env 文件已找到，请手动加载或确保环境变量已设置" -ForegroundColor Green
}

Write-Host ""
Write-Host "启动方式:"                       -ForegroundColor White
Write-Host "  Web API:  python -m api.main"  -ForegroundColor Gray
Write-Host "  CLI:      python -m cli.main -i ./chapters -o ./output/script.yaml --dry-run" -ForegroundColor Gray
Write-Host "  校验器:   python script_validator.py ./output/script.yaml" -ForegroundColor Gray
Write-Host ""

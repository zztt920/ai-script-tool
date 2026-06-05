# 演示录制辅助脚本
# 使用方法：在终端中依次执行以下步骤，配合 OBS 录制屏幕

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " AI 剧本创作工具 — 演示录制指南" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: 启动服务
Write-Host "[1/5] 启动后端服务..." -ForegroundColor Yellow
Start-Process python -ArgumentList "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"
Start-Sleep -Seconds 3

# Step 2: 打开主界面
Write-Host "[2/5] 打开主界面..." -ForegroundColor Yellow
Start-Process "http://localhost:8000/"

# Step 3: 打开 Swagger API 文档
Write-Host "[3/5] 打开 Swagger API 文档..." -ForegroundColor Yellow
Start-Process "http://localhost:8000/docs"

# Step 4: 打开 VS Code 项目目录（手动）
Write-Host "[4/5] 请手动打开 VS Code 并加载项目目录: e:\111\项目\2" -ForegroundColor Green

# Step 5: 提示开始录制
Write-Host "[5/5] 请打开 OBS Studio 或按 Win+Alt+R 开始录屏" -ForegroundColor Green
Write-Host ""
Write-Host "详细演示脚本请参考: demo_script.md" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "注意事项：" -ForegroundColor Red
Write-Host "  - 确保已配置 .env 中的 OPENAI_API_KEY" -ForegroundColor Red
Write-Host "  - 录制前清理浏览器缓存和多余标签页" -ForegroundColor Red
Write-Host "  - 建议使用 1920x1080 分辨率录制" -ForegroundColor Red
Write-Host "  - 旁白可后期配音或使用 TTS 生成" -ForegroundColor Red

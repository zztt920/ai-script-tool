# ── AI 剧本创作工具 — 一键生产部署 (Windows) ──────────
# 用法: .\deploy.ps1 [up|down|logs|status]

param (
    [string]$Action = "up"
)

Set-Location $PSScriptRoot
$ComposeFile = "docker-compose.prod.yml"

function Write-Step { Write-Host $args[0] -ForegroundColor Yellow }
function Write-OK   { Write-Host $args[0] -ForegroundColor Green  }

# ── 检查 .env ────────────────────────────────────
function Check-Env {
    if (-not (Test-Path ".env")) {
        Write-Host "[!] 未找到 .env 文件，从 .env.example 复制..." -ForegroundColor Red
        Copy-Item .env.example .env
        Write-Host "[!] 请编辑 .env 填入 OPENAI_API_KEY 后重新运行" -ForegroundColor Red
        exit 1
    }
    $content = Get-Content .env -Raw
    if ($content -match "sk-your-key-here") {
        Write-Host "[!] 检测到默认 API Key，请编辑 .env 填入真实 Key" -ForegroundColor Red
        exit 1
    }
}

# ── 生成 SSL 证书 ────────────────────────────────
function Gen-SSL {
    if (-not (Test-Path "nginx/ssl/cert.pem")) {
        Write-Step "[1/4] 生成自签名 SSL 证书..."
        & pwsh -File nginx/ssl/generate.ps1
    } else {
        Write-Step "[1/4] SSL 证书已存在，跳过"
    }
}

# ── 检查前置依赖 ──────────────────────────────────
function Check-Prereqs {
    Write-Step "[*] 检查前置依赖..."
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "[!] Docker 未安装" -ForegroundColor Red
        exit 1
    }
    Write-OK "    Docker OK"
}

# ── 启动 ─────────────────────────────────────────
function Up {
    Check-Prereqs
    Check-Env
    Gen-SSL
    Write-Step "[2/4] 构建镜像..."
    docker compose -f $ComposeFile build --no-cache
    Write-Step "[3/4] 启动服务..."
    docker compose -f $ComposeFile up -d
    Write-Step "[4/4] 等待健康检查..."
    Start-Sleep 5
    docker compose -f $ComposeFile ps
    Write-Host ""
    Write-Host "========================================"  -ForegroundColor Cyan
    Write-Host "  部署完成!"                                -ForegroundColor Cyan
    Write-Host "========================================"  -ForegroundColor Cyan
    Write-Host "  HTTPS:    https://localhost"               -ForegroundColor White
    Write-Host "  API文档:  https://localhost/docs"          -ForegroundColor White
    Write-Host "  Health:   https://localhost/health"        -ForegroundColor White
    Write-Host ""
    Write-Host "  查看日志:   .\deploy.ps1 logs"             -ForegroundColor Gray
    Write-Host "  停止服务:   .\deploy.ps1 down"             -ForegroundColor Gray
    Write-Host "  查看状态:   .\deploy.ps1 status"           -ForegroundColor Gray
    Write-Host "========================================"  -ForegroundColor Cyan
}

# ── 停止 ─────────────────────────────────────────
function Down {
    Write-Step "停止服务..."
    docker compose -f $ComposeFile down
    Write-OK "已停止"
}

# ── 日志 ─────────────────────────────────────────
function Logs {
    docker compose -f $ComposeFile logs -f --tail=100
}

# ── 状态 ─────────────────────────────────────────
function Status {
    docker compose -f $ComposeFile ps
    Write-Host ""
    Write-Host "--- API 健康检查 ---" -ForegroundColor Yellow
    try {
        $resp = Invoke-WebRequest -Uri https://localhost/health -SkipCertificateCheck -ErrorAction Stop
        Write-OK $resp.Content
    } catch {
        Write-Host "(API 未就绪)" -ForegroundColor Red
    }
}

# ── 路由 ─────────────────────────────────────────
switch ($Action) {
    "up"     { Up     }
    "down"   { Down   }
    "logs"   { Logs   }
    "status" { Status }
    default  { Write-Host "用法: .\deploy.ps1 [up|down|logs|status]" }
}

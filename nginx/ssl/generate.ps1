# ── 生成自签名 SSL 证书（本地开发用）────────────────
# 用法: .\nginx\ssl\generate.ps1
# 输出: cert.pem + key.pem 写入 nginx/ssl/

Write-Host "[1/2] 生成 2048 位 RSA 私钥..." -ForegroundColor Yellow
openssl genrsa -out key.pem 2048

Write-Host "[2/2] 生成自签名证书（有效期 365 天）..." -ForegroundColor Yellow
openssl req -new -x509 -key key.pem -out cert.pem -days 365 `
    -subj "/C=CN/ST=Beijing/L=Beijing/O=Dev/CN=localhost"

Write-Host "完成! cert.pem + key.pem 已生成" -ForegroundColor Green
Write-Host "浏览器访问时会提示不安全，点击"高级→继续访问"即可。" -ForegroundColor Gray

#!/usr/bin/env bash
# ── 生成自签名 SSL 证书（本地开发用）────────────────
# 用法: bash nginx/ssl/generate.sh
# 输出: cert.pem + key.pem 写入 nginx/ssl/
set -e

cd "$(dirname "$0")"

echo "[1/2] 生成 2048 位 RSA 私钥..."
openssl genrsa -out key.pem 2048

echo "[2/2] 生成自签名证书（有效期 365 天）..."
openssl req -new -x509 -key key.pem -out cert.pem -days 365 \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=Dev/CN=localhost"

echo "完成! cert.pem + key.pem 已生成"
echo "浏览器访问时会提示不安全，点击"高级→继续访问"即可。"

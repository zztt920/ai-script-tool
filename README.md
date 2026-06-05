# AI 剧本创作工具 — 小说转剧本

将 3 章以上小说自动转换为 YAML 格式结构化剧本的 AI 辅助创作工具。

## 演示视频

> 🎬 完整功能演示视频（含语音讲解）：
> 
>
> 百度网盘备用：**[📥 下载演示视频](通过网盘分享的文件：演示视频.mp4
链接: https://pan.baidu.com/s/16_WjegHtwi3M1PIFygcKxQ?pwd=h8ug 提取码: h8ug 复制这段内容后打开百度网盘手机App，操作更方便哦 
--来自百度网盘超级会员v4的分享)** *(待上传后替换链接)*

### 演示内容概要

| 模块 | 内容 |
|------|------|
| 项目概述 | 架构介绍、分层设计 |
| 服务启动 | 环境配置、API Key 设置 |
| 主界面 | 4 个功能页面、中英切换 |
| 提交转换 | 9 步流水线、实时进度 |
| 翻页阅读器 | 书本翻页动画、全中文剧本展示 |
| 下载导出 | YAML/JSON 多格式导出 |
| API 文档 | Swagger UI 在线调试 |
| 用户认证 | JWT 注册/登录 |
| 测试 | 31 项单元测试全部通过 |

*演示脚本详见 [demo_script.md](./demo_script.md)*

---

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/zztt920/ai-script-tool.git
cd ai-script-tool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key

# 4. 启动服务
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# 5. 打开浏览器
# 主界面: http://localhost:8000/
# API 文档: http://localhost:8000/docs
```

---

## 核心功能

### 9 步转换流水线

| 步骤 | 名称 | 说明 |
|------|------|------|
| 1 | 加载 | 读取 TXT/DOCX/PDF 章节文件 |
| 2 | 分析 | AI 分析人物关系、情节走向 |
| 3 | 提取 | 识别并提取场景边界 |
| 4 | 润色 | 优化对白和场景描写 |
| 5 | 构建 | 按风格模板构建分幕结构 |
| 6 | 撰写 | 生成结构化节拍（beat） |
| 7 | 校验 | Schema 验证数据完整性 |
| 8 | 审核 | AI 质量评估与建议 |
| 9 | 持久化 | 保存到 SQLite + YAML 文件 |

### 10 种风格模板

| 风格 | 分幕结构 | 特点 |
|------|----------|------|
| 悬疑 | 谜面→深入→转折→真相 | 推理氛围、悬念设计 |
| 甜宠 | 遇见→心动→考验→归宿 | 甜蜜互动、情感升温 |
| 热血 | 觉醒→联盟→决战→新生 | 战斗成长、羁绊深化 |
| 沙雕 | 翻车→加戏→崩盘→升华 | 幽默反转、荒诞逻辑 |
| 都市 | 交集→拉扯→抉择→归属 | 现实质感、职场生活 |
| 古装 | 入局→博弈→翻覆→定鼎 | 权谋宫斗、古典韵味 |
| 仙侠 | 入门→筑基→渡劫→飞升→开天 | 修仙体系、境界突破 |
| 科幻 | 发现→探索→危机→重生 | 未来设定、科技反思 |
| 惊悚 | 征兆→升级→崩溃→余悸 | 氛围营造、心理恐惧 |
| 自动 | AI 动态分析 | 自动推断最合适风格 |

### 书本翻页阅读器

- 📖 仿纸质书翻页动画，支持拖拽翻页
- 🎨 书籍出版风格排版，中文完整呈现
- ⌨️ 支持键盘左右箭头、点击页边翻页
- 📱 响应式设计，适配移动端和桌面端

### API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/convert` | POST | 提交小说转换任务 |
| `/api/v1/tasks` | GET | 获取任务列表 |
| `/api/v1/tasks/{id}` | GET | 获取任务详情与进度 |
| `/api/v1/tasks/{id}` | DELETE | 删除单个任务 |
| `/api/v1/tasks/batch-delete` | POST | 批量删除任务 |
| `/api/v1/tasks/stats` | GET | 仪表盘统计数据 |
| `/api/v1/tasks/search` | GET | 剧本全文搜索 |
| `/api/v1/tasks/styles` | GET | 风格模板列表 |
| `/api/v1/tasks/{id}/script` | GET | 下载 YAML 剧本 |
| `/api/v1/tasks/{id}/script.json` | GET | 导出 JSON 剧本 |
| `/api/v1/tasks/{id}/validate` | POST | Schema 校验 |
| `/api/v1/tasks/{id}/polish` | POST | AI 润色与质量审核 |
| `/auth/register` | POST | 用户注册 |
| `/auth/login` | POST | 用户登录 |
| `/auth/refresh` | POST | 刷新 JWT Token |
| `/auth/me` | GET | 获取当前用户信息 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | FastAPI + Python 3.11+ |
| 数据库 | SQLite |
| AI | DeepSeek API |
| 认证 | JWT (pyjwt + bcrypt) |
| 缓存 | Redis（可选，优雅降级） |
| 前端 | 原生 JS SPA + CSS3 动画 |
| 国际化 | 中英双语 i18n |
| CI/CD | GitHub Actions |

---

## 项目结构

```
├── domain/            # 领域模型与 Schema 校验
│   ├── models.py
│   └── schema_validator.py
├── service/           # 核心业务逻辑
│   ├── conversion_pipeline.py   # 9 步流水线
│   └── auth_service.py          # JWT 认证
├── adapter/           # 外部依赖适配器
│   ├── ai_client.py             # DeepSeek API
│   ├── cache.py                 # Redis 缓存
│   ├── logger.py                # 结构化日志
│   ├── repository.py            # 数据访问
│   ├── user_repository.py       # 用户数据
│   └── yaml_writer.py           # YAML 生成
├── api/               # API 层
│   ├── main.py                  # 应用入口
│   ├── middleware.py            # 中间件（限流/日志）
│   ├── schemas.py               # Pydantic 模型
│   ├── errors.py                # 异常处理
│   ├── routers/                 # 路由
│   └── static/                  # 前端 SPA
├── db/                # 数据库
│   └── database.py
├── tests/             # 单元测试
└── cli/               # 命令行接口
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | DeepSeek API Key | - |
| `OPENAI_API_BASE` | API 基地址 | `https://api.deepseek.com/v1` |
| `AI_MODEL` | AI 模型名称 | `deepseek-v4-flash` |
| `RATE_LIMIT_MAX` | 限流最大请求数 | `60` |
| `RATE_LIMIT_WINDOW` | 限流时间窗口（秒） | `60` |
| `REDIS_ENABLED` | 启用 Redis 缓存 | `false` |
| `REDIS_URL` | Redis 连接地址 | `redis://localhost:6379` |
| `JWT_SECRET` | JWT 签名密钥 | (随机生成) |
| `SCRIPT_DB_PATH` | 数据库文件路径 | `data/script_tool.db` |

---

## 运行测试

```bash
python -m unittest tests.test_novel_to_script -q
```

31 项测试覆盖核心转换流水线各环节。

---

## License

MIT

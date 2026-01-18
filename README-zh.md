<div align="center">
<h1 align="center">Winning CV - 职位匹配与简历定制平台</h1>

<p align="center">
  <strong>告别千篇一律的简历，让系统为每个机会量身定制完美简历</strong>
</p>

<p align="center">
  <a href="https://winning-cv.jackhui.com.au">立即体验</a> |
  <a href="#快速开始">快速开始</a> |
  <a href="#核心功能">功能介绍</a> |
  <a href="README.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/React-18+-61DAFB?logo=react" alt="React 18+">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker" alt="Docker Ready">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
</p>

</div>

---

## 即刻体验 — 无需安装

**立即在线使用：** [https://winning-cv.jackhui.com.au](https://winning-cv.jackhui.com.au)

- **零配置** — 登录即可使用
- **免费使用** （合理使用限制）
- **全功能开放** — 网页端支持所有功能

> **建议：** 先体验在线版本，了解完整功能后再考虑本地部署！

---

## 什么是 Winning CV？

Winning CV 是一款开源应用，彻底改变传统的求职方式。无需手动为每个职位修改简历，智能系统自动完成：

1. **全平台扫描** — LinkedIn、Seek、Indeed、Glassdoor、Google Jobs
2. **智能分析** — 基于NLP语义分析，将职位要求与您的简历对比
3. **匹配评分** — 0-10分匹配度，帮您精准定位最佳机会
4. **定制生成** — 为每个职位生成针对性优化的简历
5. **即时通知** — 通过邮件、Telegram、微信实时推送高匹配职位

**成效：** 更少的申请时间，更高的面试率。

---

## 核心功能

### 智能职位聚合
- 实时爬取LinkedIn、Seek、Indeed、Glassdoor、Google Jobs
- 支持地区、关键词等高级筛选
- 自动去重与优先级排序
- LinkedIn Cookie健康监控，确保爬取稳定性

### 简历智能匹配
- 基于spaCy NLP的职位描述与简历语义分析
- 0-10分匹配评分系统
- 简历-职位匹配度分析（CV-JD Fit Analysis）
- 技能差距识别与建议

### 自动化简历生成
- 基于Azure AI的上下文感知定制
- 职位关键词自动优化
- 格式完美保留（PDF/DOCX）
- 智能提炼工作亮点

### 简历版本库
- 每份简历自动版本化存储
- MinIO安全存储，支持预签名URL
- 自动分类与自定义标签
- 支持分支、归档、恢复、删除
- 使用量与回复率追踪分析
- 搜索前可从版本库选择简历

### 多渠道即时提醒
- **邮件** — 基于SMTP，支持自定义模板
- **Telegram** — 通过Bot即时推送，配置Chat ID即可
- **微信** — 通过自定义微信API直接发送消息
- 支持从个人设置发送测试通知
- 每条通知包含完整职位信息

### 现代化仪表盘
- **交互式统计** — 匹配总数、已生成简历数、平均分数
- **职位浏览器** — 筛选、排序、浏览匹配职位
- **简历分析** — 追踪各版本简历的回复率
- **效果指标** — 监控求职效率

### 认证与安全
- 微软OAuth集成
- 基于Token的API认证
- 安全会话管理
- 用户级通知偏好设置

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18, Vite, Tailwind CSS, HeroUI |
| 后端 | FastAPI, Python 3.10+ |
| 管理界面 | Streamlit + OAuth |
| 存储 | MinIO (S3兼容), Airtable |
| NLP | spaCy + en-core-web-sm |
| 容器化 | Docker, Docker Compose |

---

## 快速开始

### 方式一：Docker部署（推荐）

最快捷的一键启动方式：

```bash
# 克隆仓库
git clone https://github.com/jack-jackhui/winning-cv.git
cd winning-cv

# 创建配置文件
cp env.example .env
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# 编辑 .env 填写API密钥等配置（参见配置说明）

# 启动所有服务
docker compose up -d
```

**访问地址：**
- **React前端：** http://localhost:13000
- **FastAPI后端：** http://localhost:8000
- **API文档：** http://localhost:8000/api/docs
- **MinIO控制台：** http://localhost:9001

### 方式二：本地开发

适合开发者和需要完全控制的用户：

```bash
# 克隆并配置
git clone https://github.com/jack-jackhui/winning-cv.git
cd winning-cv

# 创建配置文件
cp env.example .env
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# 安装Python依赖（需要Python 3.10+）
pip install uv  # 或: brew install uv
uv pip install -r requirements.txt

# 安装spaCy语言模型
python -m spacy download en-core-web-sm

# 配置浏览器路径 (.env)
# macOS: CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Windows: CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
# 设置: HEADLESS=false 和 RUNNING_IN_DOCKER=false
```

**启动服务：**

```bash
# 终端1: FastAPI后端
python run_api.py
# API: http://localhost:8000, 文档: http://localhost:8000/api/docs

# 终端2: React前端（开发模式）
cd frontend && npm install && npm run dev
# 前端: http://localhost:3000

# 终端3: Streamlit管理界面
python webui_new.py
# 管理界面: http://localhost:8501

# 或运行CLI命令行
python main.py --user-email your@email.com
```

---

## 使用流程

### 网页端操作

1. **登录** — 使用微软OAuth
2. **配置搜索** — 输入职位关键词、地区等
3. **选择简历** — 从版本库选择或上传新简历
4. **运行搜索** — 系统自动抓取职位并实时评分
5. **查看匹配** — 浏览带匹配分数的职位列表
6. **下载简历** — 获取为每个职位优化的定制简历
7. **管理版本** — 追踪所有版本，查看分析数据，优化策略

### 命令行操作

```bash
# 在 .env 中设置职位搜索URL
LINKEDIN_JOB_URL=https://linkedin.com/jobs/search?keywords=...
SEEK_JOB_URL=https://seek.com.au/...

# 运行职位处理器
python main.py --user-email your@email.com
```

系统自动完成职位分析、简历生成和通知推送。

---

## 配置说明

所有配置通过 `.env` 文件管理，复制 `env.example` 并配置：

<details>
<summary><strong>点击展开完整配置参考</strong></summary>

```ini
# === 基础简历 ===
BASE_CV_PATH=user_cv/my_resume.docx

# === Airtable (数据存储) ===
AIRTABLE_PAT=your-personal-access-token
AIRTABLE_BASE_ID=your-base-id
AIRTABLE_TABLE_ID=main-jobs-table-id
AIRTABLE_TABLE_ID_HISTORY=history-table-id
AIRTABLE_TABLE_ID_USER_CONFIGS=user-configs-table-id
AIRTABLE_TABLE_ID_CV_VERSIONS=cv-versions-table-id

# === MinIO (简历文件存储) ===
MINIO_ENDPOINT=localhost:9000       # Docker中使用 minio:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_BUCKET=winningcv-cvs

# === 职位搜索URL (CLI模式) ===
LINKEDIN_JOB_URL=https://linkedin.com/jobs/search?...
SEEK_JOB_URL=https://seek.com.au/...

# === Azure AI ===
AZURE_AI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_AI_API_KEY=your-api-key
AZURE_DEPLOYMENT=deployment-name

# === 通知设置 ===
# 邮件
EMAIL_USER=your@email.com
EMAIL_PASSWORD=your-password
SMTP_SERVER=smtp.server.com
DEFAULT_FROM_EMAIL=noreply@example.com
DEFAULT_TO_EMAIL=your@email.com

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# 微信 (直接API)
WECHAT_API_URL=https://your-wechat-api.com
WECHAT_API_KEY=your-api-key

# === 搜索参数 ===
LOCATION=Melbourne,VIC
COUNTRY=Australia
HOURS_OLD=168          # 最近7天的职位
RESULTS_WANTED=10      # 每个平台的职位数
JOB_MATCH_THRESHOLD=7  # 最低匹配分数 (0-10)
MAX_JOBS_TO_SCRAPE=50

# === 浏览器配置 (本地开发) ===
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HEADLESS=false
RUNNING_IN_DOCKER=false
```

</details>

### 认证配置

在 `.streamlit/secrets.toml` 中配置OAuth：

```toml
[connections.google]
client_id = "your-google-client-id"
client_secret = "your-google-secret"
redirect_uri = "https://your-domain.com/oauth/callback"

[connections.microsoft]
client_id = "your-microsoft-client-id"
client_secret = "your-microsoft-secret"
```

详见 [Streamlit认证文档](https://docs.streamlit.io/develop/concepts/connections/authentication)。

---

## 系统架构

```
winning-cv/
├── frontend/              # React + Vite + Tailwind 仪表盘
│   └── src/
│       ├── pages/         # Dashboard, CVLibrary, Analytics, Profile 等
│       ├── components/    # 可复用UI组件
│       ├── context/       # 认证上下文
│       └── services/      # API客户端
├── api/                   # FastAPI REST 后端
│   ├── routes/            # auth, cv, cv_versions, jobs, profile
│   ├── middleware/        # 认证中间件
│   └── schemas/           # Pydantic 模型
├── job_processing/        # 核心匹配引擎
├── job_sources/           # 平台爬虫 (LinkedIn, Seek 等)
│   └── linkedin_cookie_health.py  # Cookie监控
├── data_store/            # Airtable + 简历版本管理
├── cv/                    # 简历解析与生成
├── utils/                 # MinIO存储, 通知, 日志
├── scheduler/             # APScheduler后台任务
├── webui_new.py           # Streamlit 管理应用
├── main.py                # CLI 接口
└── run_api.py             # FastAPI 服务入口
```

### Docker服务

| 服务 | 端口 | 说明 |
|------|------|------|
| `frontend` | 13000 | React SPA (Nginx) |
| `api` | 8000 | FastAPI REST后端 |
| `job-runner` | - | CLI批处理器 |
| `minio` | 9000/9001 | S3兼容对象存储 |

---

## API参考

FastAPI后端提供完整的REST API：

### 认证
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/me` | GET | 获取认证状态 |
| `/api/v1/auth/user` | GET | 获取用户信息 |
| `/api/v1/auth/login-url` | GET | 获取OAuth登录URL |
| `/api/v1/auth/logout` | POST | 登出 |

### 职位
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/jobs/config` | GET | 获取搜索配置 |
| `/api/v1/jobs/config` | POST | 保存搜索配置 |
| `/api/v1/jobs/search` | POST | 开始搜索 |
| `/api/v1/jobs/search/{task_id}/status` | GET | 获取搜索状态 |
| `/api/v1/jobs/results` | GET | 获取匹配职位列表 |
| `/api/v1/jobs/linkedin/health` | GET | LinkedIn Cookie健康状态 |

### 简历版本
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/cv/versions` | GET | 获取版本列表 |
| `/api/v1/cv/versions` | POST | 创建版本 |
| `/api/v1/cv/versions/{id}` | GET | 获取版本详情 |
| `/api/v1/cv/versions/{id}` | PATCH | 更新版本 |
| `/api/v1/cv/versions/{id}` | DELETE | 删除版本 |
| `/api/v1/cv/versions/{id}/download` | GET | 获取下载链接 |
| `/api/v1/cv/versions/{id}/fork` | POST | 分支版本 |
| `/api/v1/cv/versions/analytics/summary` | GET | 获取分析数据 |

### 个人资料与通知
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/profile/notifications` | GET | 获取通知偏好 |
| `/api/v1/profile/notifications` | PUT | 更新偏好 |
| `/api/v1/profile/notifications/test` | POST | 发送测试通知 |

完整交互文档：`http://localhost:8000/api/docs`

---

## 安全建议

```bash
# 切勿提交敏感文件
echo ".env" >> .gitignore
echo ".streamlit/secrets.toml" >> .gitignore

# 限制文件权限
chmod 600 .env .streamlit/secrets.toml
```

- 定期轮换凭证
- CI/CD中使用环境变量
- 妥善保管API密钥和令牌
- 参阅 [Streamlit安全建议](https://docs.streamlit.io/develop/concepts/connections/authentication#security-considerations)

---

## 开发路线

- [ ] 支持Ollama本地大模型
- [ ] 一键申请浏览器插件
- [ ] 薪资谈判助手
- [ ] 申请成功率分析仪表盘
- [ ] 移动端应用 (iOS/Android)
- [ ] 更多招聘平台接入
- [ ] 社区插件市场

---

## 参与贡献

欢迎参与项目开发！

- **提交Bug** — 通过 [GitHub Issues](https://github.com/jack-jackhui/winning-cv/issues)
- **提交PR** — 新功能和Bug修复
- **开发连接器** — 接入新的招聘平台
- **完善文档** — 改进说明和教程
- **分享经验** — 告诉我们您的成功故事

提交PR前请阅读 [贡献指南](CONTRIBUTING.md)。

---

## 许可协议

基于 [MIT协议](LICENSE) 开源。

---

## 免责声明

- 职位数据来自第三方平台
- 用户需遵守各平台的服务条款
- 生成的简历请务必人工审核后再提交
- 本项目与LinkedIn、Seek、Indeed等平台无隶属关系

---

<div align="center">

**开启智能求职新时代**

[立即免费体验](https://winning-cv.jackhui.com.au) | [查看文档](https://github.com/jack-jackhui/winning-cv)

**点击 ⭐ Star 支持项目发展！**

</div>

---

## 致谢

本项目基于以下优秀开源技术构建：

- **[JobSpy](https://github.com/speedyapply/JobSpy)** — 多平台职位爬取
- **[FastAPI](https://fastapi.tiangolo.com)** — 现代Python Web框架
- **[React](https://react.dev)** — UI组件库
- **[HeroUI](https://heroui.com)** — React组件库
- **[Streamlit](https://streamlit.io)** — 快速仪表盘开发
- **[MinIO](https://min.io)** — S3兼容对象存储
- **[spaCy](https://spacy.io)** — 工业级NLP
- **[Docker](https://docker.com)** — 容器化技术

*特别感谢所有开源维护者和贡献者，正是你们让此类项目成为可能。*

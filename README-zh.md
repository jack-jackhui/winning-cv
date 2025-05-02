<div align="center">
<h1 align="center">🚀 Winning CV - 智能简历优化与职位匹配系统</h1>

<h3><a href="README.md">English</a> | 简体中文</h3>

</div>

## 项目介绍 📌
Winning CV 是一款开源的AI求职助手，通过智能匹配岗位需求与个人简历，自动生成定制化求职材料。系统核心功能：

- 实时监控主流招聘平台
- 智能分析岗位匹配度
- 自动生成定制简历
- 精准推送优质岗位

**海投时代已经结束** - 让AI为每个岗位精准定制简历！

当然！这是对应的中文说明（可放在 README 的“介绍”后或“使用说明”前，适应你项目结构即可）：

---

## 新版交互式 UI 工作流 🚦

### 直接在 Web 界面搜索职位

Winning CV 现已支持**全新网页界面**，你可以直接在浏览器中配置职位搜索，一键生成专属简历，无需编程基础！

**你可以：**
- 直接在应用内跨平台搜索职位（LinkedIn、Seek、Indeed、Glassdoor 等）
- 保存并随时更新你的搜索配置
- 针对每个职位一键生成定制化简历

### 使用流程

1. **配置你的搜索条件**
   - 在网页界面选择 **“运行职位搜索”** 功能。
   - 上传你的基础简历（PDF 或 DOCX 格式）。
   - 输入你的期望条件：地区、关键词、职位数量等。
   - 针对支持的平台，粘贴相应的职位搜索网址。

2. **LinkedIn 与 Seek 集成**
   - **LinkedIn**：请在 LinkedIn 职位搜索页筛选好条件后，复制当前网页的搜索结果 URL 粘贴到应用中。
   - **Seek**：同样，在 seek.com.au 筛选职位后，复制搜索结果页的网址粘贴到应用中。
   - 应用会自动抓取你指定链接下的所有职位信息。

3. **保存并运行**
   - 每位用户的搜索配置会被保存，如有修改会自动更新，无需重复填写。
   - 点击 **“保存并运行搜索”**，系统会自动聚合各大平台的职位数据。
   - 应用将你的简历与每个职位进行智能分析和匹配，展示所有高匹配岗位及定制简历下载链接。

4. **查看与管理结果**
   - 实时查看每个职位的匹配详情与分析分数。
   - 一键下载专属定制简历。
   - 可随时编辑搜索配置，优化搜索结果。

### 支持的平台

- **LinkedIn**：粘贴你自定义的搜索结果网址
- **Seek**：粘贴你自定义的搜索结果网址
- **Indeed、Glassdoor、Google Jobs**：输入关键词或搜索词，系统自动智能聚合

> **提示：**
> 职位抓取效果取决于你粘贴的网址。
> 建议先在各大平台筛选好你的理想职位，再复制搜索页的网址到应用中。

---

## 网页端使用示例

1. **打开网页端仪表盘**
   ```
   python webui_new.py
   ```
   然后在浏览器访问 [http://localhost:8501](http://localhost:8501)。

2. **配置你的搜索条件**
   - 上传你的基础简历
   - 粘贴各职位平台的搜索结果网址，例如：
     - `https://www.linkedin.com/jobs/search/?keywords=data+scientist&location=Melbourne`
     - `https://www.seek.com.au/data-scientist-jobs/in-Melbourne`
   - 自定义其他搜索参数（地区、关键词等）

3. **一键运行与查看结果**
   - 点击 **保存并运行搜索**
   - 实时查看所有匹配职位及匹配分数
   - 针对每个职位一键下载专属简历

---

## 为什么需要粘贴职位网址？
对于 LinkedIn 和 Seek 等职位平台，系统依赖你提供的搜索结果网址来抓取最相关的职位。这种方式可以：
- 让你灵活控制所有搜索与筛选条件
- 保证应用抓取与你实际需求一致的最新职位
- 支持你随时变更搜索偏好

---

**用新版 Winning CV 网页界面和精准职位聚合，彻底升级你的求职体验！**

---

## 核心功能 🔥
### 🔍 智能职位聚合
- 实时爬取领英/Seek/Indeed等平台（持续扩展中）
- 支持地理位置/薪资范围/经验要求筛选 (持续扩展中)
- 自动去重与优先级排序

### 🎯 简历智能匹配
- 职位描述与基础简历的语义分析
- 匹配度评分系统（0-100%）
- 技能差距分析与提升建议

### ✨ 自动化简历生成
- 上下文感知的简历定制
- 岗位关键词自动优化
- 格式完美保留（PDF/DOCX/TXT）
- AI成就亮点挖掘

### 📬 多渠道即时提醒
- 邮件/Telegram/微信通知
- 每日/每周摘要推送
- 高匹配岗位即时提醒

### 🌐 开放可扩展架构
- 完全掌控个人数据
- 模块化设计支持自定义扩展
- 社区插件支持（即将推出）

### 🤖 AI核心引擎
- 深度集成Azure AI（DeepSeek R1）
- 即将支持Ollama本地大模型
- 可定制的提示词工程

## 🚀 快速开始

欢迎使用 Winning CV！本项目支持**快速 Docker 部署**（强烈推荐）和**本地手动安装**（适合开发者和高级用户）。
所有配置均通过 `.env` 文件集中管理。

---

### 🟢 方式一：Docker 快速部署（推荐）

1. **克隆本仓库（或仅下载 docker-compose.yml 和 .env.example）**
   ```bash
   git clone https://github.com/jack-jackhui/winning-cv.git
   cd winning-cv
   ```

2. **创建你的 `.env` 配置文件**
   ```bash
   cp env.example .env
   ```
   编辑 `.env`，填写所有必需配置项（详见[下方配置说明](#配置)）。

3. **（可选，推荐）检查并编辑 `docker-compose.yml`**

   示例 `docker-compose.yml`（详情参见仓库）：
   ```yaml
   version: '3.8'
   services:
     winning-cv:
       image: ghcr.io/jack-jackhui/winning-cv:latest
       container_name: winning-cv
       restart: unless-stopped
       ports:
         - "13000:8501"  # 主机端口 13000 映射到容器 8501
       volumes:
         - ./user_cv:/winning-cv/user_cv
         - cv_data:/winning-cv/customised_cv
       env_file:
         - .env
   volumes:
     cv_data:
   ```

4. **启动应用**
   ```bash
   docker compose up -d
   ```

5. **访问 Web 界面**
   - 浏览器访问 [http://localhost:13000](http://localhost:13000)

6. **查看日志（可选）**
   ```bash
   docker compose logs -f winning-cv
   ```

> **注意：**
> 必须拥有有效的 `.env` 文件并正确填写所有参数。
> 所有配置（API 密钥、爬取网址、通知设置等）均从该文件读取。

---

### 🧑‍💻 方式二：本地手动安装（开发/高级用户）

1. **克隆仓库**
   ```bash
   git clone https://github.com/jack-jackhui/winning-cv.git
   cd winning-cv
   ```

2. **创建 `.env` 配置文件**
   ```bash
   cp env.example .env
   ```
   按下方说明填写配置。

3. **安装依赖**
   - 需 Python 3.10+ 环境
   - 需安装最新版 Google Chrome 浏览器，并在 `.env` 中正确配置其路径
   - 推荐使用 [uv](https://github.com/astral-sh/uv) 安装依赖（或用 pip）

4. **安装 Python 依赖**
   ```bash
   uv pip install -r requirements.txt
   ```

5. **下载并安装 spaCy 语言模型**
   ```bash
   python -m spacy download en-core-web-sm
   python -c "import spacy; nlp = spacy.load('en_core_web_sm')"
   ```

6. **在 `.env` 中配置浏览器路径**
   - **macOS 示例：**
     ```ini
     CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
     HEADLESS=false
     RUNNING_IN_DOCKER=false
     ```
   - **Windows 示例：**
     ```ini
     CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
     HEADLESS=false
     RUNNING_IN_DOCKER=false
     ```

7. **本地运行应用**
   - 启动 Web 界面：
     ```bash
     python webui_new.py
     ```
     浏览器访问 [http://localhost:8501](http://localhost:8501)
   - 运行命令行任务：
     ```bash
     python main.py --user-email <your-email>
     ```

---

## ⚙️ 配置

所有配置均通过项目根目录下的 `.env` 文件统一管理。
**请先复制** `.env.example` 到 `.env`，再填写各项参数。

<details>
<summary>点击展开完整 <code>.env.example</code> 模板</summary>

```ini
# === 基础简历配置 ===
BASE_CV_PATH=你的基础简历文档路径

# === Airtable 配置 ===
AIRTABLE_PAT=你的 Airtable 个人访问令牌
AIRTABLE_BASE_ID=你的 Airtable Base ID
AIRTABLE_TABLE_ID=主表格 ID
AIRTABLE_TABLE_ID_HISTORY=历史记录表格 ID

# === 职位爬取网址 ===
LINKEDIN_JOB_URL=https://linkedin.com
SEEK_JOB_URL=https://seek.com

# === Azure AI 配置 ===
AZURE_AI_ENDPOINT=https://your-azure-endpoint.openai.azure.com
AZURE_AI_API_KEY=你的 Azure AI API Key
AZURE_DEPLOYMENT=你的部署名

# === 通知设置 ===
TELEGRAM_BOT_TOKEN=Telegram Bot Token
TELEGRAM_CHAT_ID=Telegram 聊天 ID
WECHAT_API_KEY=微信 API Key
WECHAT_BOT_URL=微信 Webhook 地址
EMAIL_USER=你的邮箱账号
EMAIL_PASSWORD=邮箱密码
SMTP_SERVER=SMTP服务器地址
DEFAULT_FROM_EMAIL=发信邮箱
DEFAULT_TO_EMAIL=默认收件邮箱

# === 职位搜索参数 ===
LOCATION=Melbourne,VIC
COUNTRY=australia
HOURS_OLD=168
RESULTS_WANTED=10
JOB_MATCH_THRESHOLD=7
MAX_JOBS_TO_SCRAPE=50
CHECK_INTERVAL_MIN=60

# === 浏览器配置 ===
CHROME_PATH="/path/to/chrome"      # 本地开发专用
CHROMIUM_PATH="/usr/bin/chromium"  # Docker 专用
HEADLESS="true"                    # Docker 填 true，本地填 false
RUNNING_IN_DOCKER="false"          # Docker 自动设置

# === 高级搜索配置 ===
ADDITIONAL_SEARCH_TERM='AI IT (manager OR head OR director) "software engineering" leadership'
GOOGLE_SEARCH_TERM='head of IT or IT manager jobs near [Location] since last week'
```
</details>

---

### 🔑 主要配置说明

- **BASE_CV_PATH**：你的基础简历文档路径（如 `user_cv/my_cv.docx`）
- **Airtable 相关**：`AIRTABLE_PAT`、`AIRTABLE_BASE_ID`、`AIRTABLE_TABLE_ID`、`AIRTABLE_TABLE_ID_HISTORY`
- **职位爬取网址**：
  - `LINKEDIN_JOB_URL`：定制化 Linkedin 职位搜索网址
  - `SEEK_JOB_URL`：定制化 Seek 职位搜索网址
- **Azure AI**：`AZURE_AI_ENDPOINT`、`AZURE_AI_API_KEY`、`AZURE_DEPLOYMENT`
- **通知通道**：
  - Telegram：`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  - 微信：`WECHAT_API_KEY`, `WECHAT_BOT_URL`
  - 邮件：`EMAIL_USER`, `EMAIL_PASSWORD`, `SMTP_SERVER`, `DEFAULT_FROM_EMAIL`, `DEFAULT_TO_EMAIL`
- **职位搜索参数**：`LOCATION`、`COUNTRY`、`HOURS_OLD`、`RESULTS_WANTED`、`JOB_MATCH_THRESHOLD`、`MAX_JOBS_TO_SCRAPE`、`CHECK_INTERVAL_MIN`
- **浏览器配置**：
  - Docker 环境：`CHROMIUM_PATH=/usr/bin/chromium`, `HEADLESS=true`, `RUNNING_IN_DOCKER=true`
  - 本地开发：`CHROME_PATH`, `HEADLESS=false`, `RUNNING_IN_DOCKER=false`

> **提示：**
> 大多数参数有默认值，但请根据你的实际需求调整搜索网址和通知设置。

---

### 🛡️ 安全与最佳实践

- **绝不要提交你的 `.env` 文件**（请将 `.env` 加入 `.gitignore`）
- API Key、令牌、密码等敏感信息务必妥善保管
- 建议使用 Docker 卷或本地目录保证数据持久化
- 多人协作开发时，如有新增配置项，请同步更新 `.env.example`

---

## 🚦 使用方法

**Web 界面**
- **Docker 部署：** 浏览器访问 [http://localhost:13000](http://localhost:13000)
- **本地开发：** 运行 `python webui_new.py`，浏览器访问 [http://localhost:8501](http://localhost:8501)

**命令行批量任务（Docker）：**
```bash
docker compose run --rm job-runner
```
**命令行批量任务（本地）：**
```bash
python main.py --user-email <你的邮箱>
```

---

## 总结

- **Docker 部署**：简单快捷，推荐绝大多数用户使用
- **手动安装**：适合开发者深度定制
- **所有配置**：集中在 `.env` 文件（建议从 `.env.example` 复制）
- **安全建议**：敏感信息请勿上传到代码仓库

## 开发路线 🗺️
- [ ] 接入更多招聘平台
- [ ] 支持Ollama本地大模型
- [ ] 开发一键申请浏览器插件
- [ ] 薪资谈判助手
- [ ] 申请成功率分析
- [ ] 移动端应用（iOS/Android）
- [ ] 社区插件市场

## 贡献指南 🤝
欢迎开发者加入我们的开源项目！参与方式包括：
- 在GitHub提交问题报告
- 提交新功能/修复的PR
- 开发平台连接器
- 完善项目文档
- 制作使用教程

**贡献前请务必阅读[贡献指南](CONTRIBUTING.md)**

## 许可协议 📄
本项目采用[MIT许可证](LICENSE)

## 免责声明 ⚠️
- 职位数据来自第三方平台
- 用户需自行遵守各平台服务条款
- 生成简历需人工审核后方可提交
- 本项目与领英/Seek/Indeed无隶属关系

---

**开启智能求职新时代** - 点击⭐星标支持项目发展！
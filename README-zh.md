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

## 快速开始 🛠️
### 环境要求
- Python 3.10+
- 大模型API密钥（Azure OpenAI 或本地Ollama）

### 安装步骤
```bash
git clone https://github.com/jack-jackhui/winning-cv.git
cd winning-cv
pip install -r requirements.txt
```
#### Install base requirements
```
uv pip install -r requirements.txt
```
#### Download spaCy model
```
python -m spacy download en-core-web-sm
```
#### Verify installation
```
python -c "import spacy; nlp = spacy.load('en_core_web_sm')"
```
### 配置说明
1. 复制环境文件：
```bash
cp .env.example .env
```
2. 编辑配置参数：
**`.env.example`**
```ini
# === Base CV Configuration ===
BASE_CV_PATH=Path-to-your-base-CV-file 

# === Airtable Configuration ===
AIRTABLE_PAT=your-airtable-personal-access-token
AIRTABLE_BASE_ID=your-base-id
AIRTABLE_TABLE_ID=your-main-table-id
AIRTABLE_TABLE_ID_HISTORY=your-history-table-id

# === Linkedin & Seek URLs for Scraping Jobs ===
LINKEDIN_JOB_URL=https://linkedin.com
SEEK_JOB_URL=https://seek.com

# === Azure AI Configuration ===
AZURE_AI_ENDPOINT=https://your-azure-endpoint.openai.azure.com
AZURE_AI_API_KEY=your-azure-ai-api-key
AZURE_DEPLOYMENT=your-deployment-name

# === Notification Settings ===
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
WECHAT_API_KEY=your-wechat-api-key
WECHAT_BOT_URL=https://your-wechat-webhook-url
EMAIL_USER=your-email@domain.com
EMAIL_PASSWORD=your-email-password
SMTP_SERVER=your-smtp-server.com
DEFAULT_FROM_EMAIL=no-reply@yourdomain.com
DEFAULT_TO_EMAIL=user@domain.com

# === Job Search Parameters ===
LOCATION=Melbourne,VIC
COUNTRY=australia
HOURS_OLD=168
RESULTS_WANTED=10
JOB_MATCH_THRESHOLD=7
MAX_JOBS_TO_SCRAPE=50
CHECK_INTERVAL_MIN=60

# === Advanced Configuration ===
ADDITIONAL_SEARCH_TERM='AI IT (manager OR head OR director) "software engineering" leadership'
GOOGLE_SEARCH_TERM='head of IT or IT manager jobs near [Location] since last week'
```
---

## 配置参数说明 🔧

在项目根目录创建 `.env` 文件并配置以下参数：

### 核心服务配置
- `BASE_CV_PATH`: 基础简历文件路径 (例："user_cv/my_cv.docx")
- `AIRTABLE_PAT`: Airtable 个人访问令牌
- `AIRTABLE_BASE_ID`: Airtable 数据库ID
- `AIRTABLE_TABLE_ID`: 主职位存储表ID
- `AIRTABLE_TABLE_ID_HISTORY`: 简历生成历史表ID

### AI 服务配置
- `AZURE_AI_ENDPOINT`: Azure AI 服务终端地址
- `AZURE_AI_API_KEY`: Azure AI API 密钥
- `AZURE_DEPLOYMENT`: Azure 部署名称

### 招聘平台URL
- `LINKEDIN_JOB_URL`: LinkedIn 职位爬取地址
- `SEEK_JOB_URL`: Seek 职位爬取地址

### 通知服务配置
- `TELEGRAM_BOT_TOKEN`: Telegram 机器人令牌
- `TELEGRAM_CHAT_ID`: Telegram 通知频道ID
- `WECHAT_API_KEY`: 微信API凭证
- `WECHAT_BOT_URL`: 微信机器人Webhook地址
- 邮件服务配置 (`EMAIL_USER`, `EMAIL_PASSWORD`, `SMTP_SERVER`)

### 职位搜索参数（Indeed/Glassdoor/Google）
- `LOCATION`: 默认搜索地区 (例："Melbourne,VIC")
- `COUNTRY`: 目标国家/地区）
- `HOURS_OLD`: 职位信息最大时效（小时）
- `RESULTS_WANTED`: 各平台获取结果数量
- **可选参数**：匹配阈值 (`JOB_MATCH_THRESHOLD`) 和爬取限制 (`MAX_JOBS_TO_SCRAPE`)

### 默认参数
系统已预设合理默认值：
- 检查间隔：60 分钟
- 最大描述长度：15,000 字符
- 包含AI/IT管理岗的搜索关键词

**重要提示**： 
1. 复制 `.env.example` 为 `.env` 并替换示例值
2. 务必妥善保管此文件，禁止提交到版本控制系统
3. 实际值需根据您的服务配置进行设置

```ini
# === 示例配置 ===
EMAIL_USER=your-email@example.com
SMTP_SERVER=smtp.example.com
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghijkl-567MNOPQrs
```

## 使用指南 🚦
1. **设置基础简历**
```bash
python main.py --setup-cv 您的简历.pdf
```

2. **启动职位监控**
```bash
python main.py --daemon
```

3. **访问控制面板**
```bash
python webui_new.py  # 本地访问 http://localhost:8501
```

4. **生成定制简历**
```bash
python main.py --generate-cv 岗位ID_12345
```

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
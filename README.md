<div align="center">
<h1 align="center">🚀 Winning CV - AI Powered Job Matching & CV Tailoring App</h1>

<h3>English | <a href="README-zh.md">简体中文</a></h3>

</div>

## Introduction 📌
Winning CV is an open-source AI app that revolutionizes job applications by automatically matching your qualifications with opportunities and generating tailored resumes. Our smart system:

- Scans major job platforms in real-time
- Analyzes requirements against your base CV
- Generates customized application materials
- Alerts you to perfect matches

**Stop sending generic resumes** - Get AI-powered precision targeting for every application!

## Key Features 🔥
### 🔍 Smart Job Aggregation
- Real-time crawling of LinkedIn, Seek, Indeed (with more platforms)
- Advanced filtering by location, salary, experience level (coming soon)
- Automatic duplicate detection and priority sorting

### 🎯 CV-to-Job Matching Engine
- Semantic analysis of job descriptions vs your base CV
- Compatibility scoring system (0-10)
- Skills gap identification with improvement suggestions (coming soon)

### ✨ Auto-CV Generation
- Context-aware resume customization
- Position-specific keyword optimization
- Formatting preservation (PDF/DOCX/TXT)
- LLM-powered achievement highlighting

### 📬 Multi-Channel Alerts
- Email/Telegram/WeChat(coming soon) notifications
- Daily/weekly digest options
- Instant matching alerts for premium listings

### 🌐 Open & Extensible
- Full control over your data
- Modular architecture for custom integrations
- Community plugin support (coming soon)

### 🤖 AI-Powered Core
- Azure AI integration (DeepSeek R1)
- Local LLM support via Ollama (coming soon)
- Customizable prompt engineering

## Getting Started 🛠️
### Prerequisites
- Python 3.10+
- LLM API key (Azure OpenAI or local Ollama instance)

### Installation
```bash
git clone https://github.com/jack-jackhui/winning-cv.git
cd winning-cv
pip install -r requirements.txt
```

### Configuration
1. Copy `.env.example` to `.env`
2. Configure your settings:

**`.env.example`**
```ini
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

## Configuration Values 🔧

Create `.env` file in project root with these required values:

### Essential Services
- `AIRTABLE_PAT`: Airtable Personal Access Token
- `AIRTABLE_BASE_ID`: Your Airtable base ID
- `AIRTABLE_TABLE_ID`: Main table ID for job storage
- `AIRTABLE_TABLE_ID_HISTORY`: History table ID for CV generations

### AI Services
- `AZURE_AI_ENDPOINT`: Azure AI endpoint URL
- `AZURE_AI_API_KEY`: Azure AI API key
- `AZURE_DEPLOYMENT`: Azure deployment name

### Linked and Seek URL
- `LINKEDIN_JOB_URL`: Linkedin URL for scraping jobs
- `SEEK_JOB_URL`: Seek URL for scraping jobs

### Notifications
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for alerts
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID
- `WECHAT_API_KEY`: WeChat API credentials
- `WECHAT_BOT_URL`: WeChat webhook URL
- Email settings (`EMAIL_USER`, `EMAIL_PASSWORD`, `SMTP_SERVER`)

### Job Search Parameters (For Indeed, Glassdoor & Google)
- `LOCATION`: Default search location (e.g., "Melbourne,VIC")
- `COUNTRY`: Target country for job search
- `HOURS_OLD`: Max age of job listings (hours)
- `RESULTS_WANTED`: Number of results per platform
- **Optional**: Adjust matching threshold (`JOB_MATCH_THRESHOLD`) and scraping limits (`MAX_JOBS_TO_SCRAPE`)

### Default Values
Most parameters have sensible defaults:
- Check interval: 60 minutes
- Max description length: 15,000 characters
- Search terms include AI/IT leadership roles

**Note**: Copy `.env.example` to `.env` and replace placeholder values with your actual credentials. Keep this file secure and never commit it to version control.

```

## Usage 🚦
1. **Set Base CV**
```bash
python main.py --setup-cv path/to/your_cv.pdf
```

2. **Start Job Monitoring**
```bash
python main.py --daemon
```

3. **Access Dashboard**
```bash
python webui_new.py  # Local web interface at http://localhost:8501
```

4. **Generate Tailored CV**
```bash
python main.py --generate-cv JOB_ID_12345
```

## Roadmap 🗺️
- [ ] Add more job sources integration
- [ ] Local LLM support with Ollama
- [ ] Browser extension for one-click applications
- [ ] Salary negotiation assistant
- [ ] Application success analytics
- [ ] Mobile app (iOS/Android)
- [ ] Community plugin marketplace

## Contribution & Support 🤝
We welcome developers to join our mission! Here's how you can help:
- Report issues in GitHub Issues
- Submit PRs for new features/bug fixes
- Develop platform connectors
- Improve documentation
- Create tutorial content

**Before contributing,** please read our [Contribution Guidelines](CONTRIBUTING.md).

## License 📄
Released under [MIT License](LICENSE). 

## Disclaimer ⚠️
- Job data comes from third-party platforms
- Users are responsible for complying with platform ToS
- Always verify generated CVs before submission
- Not affiliated with LinkedIn/Seek/Indeed

---

**Transform Your Job Search** - Star ⭐ this repo to support development!
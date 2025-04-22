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
- Email/Telegram/WeChat notifications
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
```ini
# Azure AI Settings
AZURE_OPENAI_KEY=your-key-here
AZURE_ENDPOINT=https://your-endpoint.openai.azure.com

# Job Sources


# Notification Channels
EMAIL_HOST=your-smtp-server
TELEGRAM_BOT_TOKEN=your-bot-token
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
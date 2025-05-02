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


---

## New Interactive UI Workflow 🚦

### Search for Jobs Directly from the Web App

Winning CV now features an enhanced **web-based user interface** where you can configure your job search and generate tailored CVs without writing a single line of code!

**You can:**
- Search for jobs directly from the app, across multiple job platforms.
- Save your search configurations and update them any time.
- Generate customized CVs for each job with a single click.

### How It Works

1. **Configure Your Search**
   - In the web UI, go to the **"Run Job Search"** section.
   - Upload your base CV (PDF or DOCX).
   - Enter your preferences: location, keywords, number of jobs, etc.
   - For each supported job board, provide the relevant search URL.

2. **LinkedIn & Seek Integration**
   - **LinkedIn:** Paste any LinkedIn job search results URL (for example, after filtering for your desired roles or location on LinkedIn Jobs).
   - **Seek:** Paste any Seek search results URL (after applying filters on seek.com.au).
   - The app will scrape jobs from the URLs you provide, so make sure the URLs represent your search criteria.

3. **Save & Run**
   - Your configuration is saved per user and updated automatically if you change your preferences.
   - Click **"Save & Run Search"** to aggregate job postings from the specified platforms.
   - The app will analyze each job description against your CV and display a list of matches, complete with compatibility scores and download links for tailored resumes.

4. **View & Manage Results**
   - See detailed matching breakdowns for each job found.
   - Download application-ready, AI-tailored CVs instantly.
   - Edit your search configuration any time to refine your job search.

### Supported Job Platforms

- **LinkedIn:** Paste your custom search results URL.
- **Seek:** Paste your custom search results URL.
- **Indeed, Glassdoor, Google Jobs:** Enter keywords or search terms for additional AI-driven aggregation.

> **Note:**
> The quality and relevance of jobs depend on the URLs you provide.
> For best results, use the official job search and filtering tools on each platform to create URLs reflecting your interests, then copy those URLs into the app.

---

## Example: Using the Web App

1. **Open the Web Dashboard**
   ```
   python webui_new.py
   ```
   Then visit [http://localhost:8501](http://localhost:8501) in your browser.

2. **Configure Your Search**
   - Upload your base CV.
   - Paste your job board search URLs:
     - e.g., `https://www.linkedin.com/jobs/search/?keywords=data+scientist&location=Melbourne`
     - e.g., `https://www.seek.com.au/data-scientist-jobs/in-Melbourne`
   - Set job search preferences (location, keywords, etc).

3. **Run and Review**
   - Click **Save & Run Search**.
   - Instantly view all matching jobs with their compatibility scores.
   - Download custom CVs for each match.

---

## Why Provide URLs?
For job boards like LinkedIn and Seek, the app relies on your search URLs to fetch the most relevant jobs for you. This approach:
- Offers you total control over search filters and criteria.
- Ensures the app always works with the latest job postings displayed to you.
- Makes the system compatible with changing user preferences or platform UI.

---

**Upgrade your job search workflow with the new Winning CV web UI and precision job aggregation!**

---

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
Here's the updated README with Docker-related additions:

```markdown
<div align="center">
[...existing header content unchanged...]
</div>

## Development Environments 🖥️

### Local Development (macOS/Windows)
- Requires Chrome browser installed
- Uses local Chrome instance for scraping
- Set these environment variables in `.env`:
  ```ini
  CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" # macOS
  # CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe" # Windows
  HEADLESS=false
  RUNNING_IN_DOCKER=false
  ```

### Docker Deployment
- Uses built-in Chromium browser
- Automatic headless mode configuration
- Set these variables in `docker-compose.yml`:
  ```yaml
  environment:
    - CHROMIUM_PATH=/usr/bin/chromium
    - HEADLESS=true
    - RUNNING_IN_DOCKER=true
  ```

## Getting Started 🛠️

### Docker Deployment (Recommended)

1. **Build and Run**
Download the docker-compose.yml file from this repo.
   ```bash
   docker compose up -d --build
   ```

2. **Access Web UI**
   ```bash
   docker compose exec winning-cv streamlit run webui_new.py
   ```
   Visit `http://localhost:13000`

3. **View Logs**
   ```bash
   docker compose logs -f winning-cv
   ```

### Docker Configuration
Example `docker-compose.yml`:
```yaml
services:
  winning-cv:
    build: .
    ports:
      - "8501:8501"
    environment:
      - CHROMIUM_PATH=/usr/bin/chromium
      - HEADLESS=true
      - RUNNING_IN_DOCKER=true
      - AZURE_AI_API_KEY=your-azure-key
      - AIRTABLE_PAT=your-airtable-token
    volumes:
      - ./user_cv:/app/user_cv
```

### Manual Installation
### Prerequisites
- Python 3.10+
- LLM API key (Azure OpenAI or local Ollama instance)
```bash
git clone https://github.com/jack-jackhui/winning-cv.git
cd winning-cv
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

### Configuration
1. Copy `.env.example` to `.env`
2. Configure your settings:

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
# Browser Configuration
CHROME_PATH="/path/to/chrome"      # Local development only
CHROMIUM_PATH="/usr/bin/chromium"  # Docker only
HEADLESS="true"                    # true for Docker, false for local
RUNNING_IN_DOCKER="false"          # Auto-set in Docker
# === Advanced Configuration ===
ADDITIONAL_SEARCH_TERM='AI IT (manager OR head OR director) "software engineering" leadership'
GOOGLE_SEARCH_TERM='head of IT or IT manager jobs near [Location] since last week'
```
---

## Configuration Values 🔧

Create `.env` file in project root with these required values:

### Essential Services
- `BASE_CV_PATH`: Path to your base CV document (e.g., "user_cv/my_cv.docx")
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

## Usage 🚦
1. **Start Job Monitoring**
```bash
python main.py --user-email <your-email>
```

2. **Access Dashboard**
```bash
python webui_new.py  # Local web interface at http://localhost:8501
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
<div align="center">
<h1 align="center">🚀 Winning CV - AI Powered Job Matching & CV Tailoring App</h1>

<h3>English | <a href="README-zh.md">简体中文</a></h3>

</div>
---
## 🌐 Try It Instantly – No Installation Needed!
**Use Winning CV right now at:**  
[https://winning-cv.jackhui.com.au](https://winning-cv.jackhui.com.au)
- **No setup required**
- **Free to use** (subject to fair use & platform limits)
- **All features available via the web**
> 💡 **Recommended:** Try the hosted web version before installing locally or via Docker!
---
## Introduction 📌
Winning CV is an open-source AI app that revolutionizes job applications by automatically matching your qualifications with opportunities and generating tailored resumes. Our smart system:

- Scans major job platforms in real-time
- Analyzes requirements against your base CV
- Generates customized application materials
- Alerts you to perfect matches

**Stop sending generic resumes** - Get AI-powered precision targeting for every application!

---

## Authentication Configuration 🔐
Winning CV uses Streamlit's built-in authentication system. To configure authentication providers (Google, GitHub, etc.), you'll need to set up a `secrets.toml` file.

### 1. Create secrets.toml
Create a `.streamlit` directory in your project root and add `secrets.toml`:

```bash
mkdir -p .streamlit
touch .streamlit/secrets.toml
```

### 2. Configure Authentication Providers
Example configuration for Google OAuth:
```toml
# .streamlit/secrets.toml
[connections]
[connections.google]
client_id = "your-client-id.apps.googleusercontent.com"
client_secret = "your-client-secret"
redirect_uri = "https://your-domain.com/oauth/callback"
```

For other providers (GitHub, AzureAD, etc.), see [Streamlit Authentication Documentation](https://docs.streamlit.io/develop/concepts/connections/authentication).

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
   - For each supported job board, provide the relevant search parameters.

2. **LinkedIn & Seek Integration**
   - LinkedIn: Just enter your desired job keywords, location, and other search preferences. The app will automatically construct a LinkedIn job search and retrieve relevant postings – no need to manually copy/paste LinkedIn URLs.
   - Seek: Similarly, specify your job search parameters (e.g., category, location, salary range), and the app will generate the Seek search behind the scenes.
   - The app uses your provided search criteria to fetch jobs directly from these platforms, ensuring you always get results matching your preferences.
   - Linkedin & Seek URLs are still required when running the app in command line

3. **Save & Run**
   - Your configuration is saved per user and updated automatically if you change your preferences.
   - Click **"Save & Run Search"** to aggregate job postings from the specified platforms.
   - The app will analyze each job description against your CV and display a list of matches, complete with compatibility scores and download links for tailored resumes.

4. **View & Manage Results**
   - See detailed matching breakdowns for each job found.
   - Download application-ready, AI-tailored CVs instantly.
   - Edit your search configuration any time to refine your job search.

### Supported Job Platforms

- **LinkedIn:** Enter your desired search keywords and other parameters.
- **Seek:** Enter your desired search keywords and other parameters.
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

**Web UI:**
You no longer need to provide job board URLs! Simply enter your job search keywords, location, and other preferences in the web interface, and the app will automatically generate and use the appropriate search URLs for LinkedIn, Seek, and other platforms. This makes job searching easier and more intuitive.

**Command Line:**
If you use the command-line interface, you still need to provide the job board search result URLs (such as for LinkedIn or Seek) in your `.env` configuration file. The CLI relies on these URLs to fetch and match relevant jobs according to your criteria.

- **Web UI:** No URL input required—just fill in your preferences.
- **CLI:** URLs must still be specified in `.env`.

This ensures:
- Maximum flexibility and ease of use in the web version.
- Continued support for advanced or automated CLI workflows.

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

## 🚀 Getting Started

Welcome! Winning CV supports both **easy Docker deployment** (recommended for most users) and **manual local installation** (for developers and advanced users).
All configuration is managed through a single `.env` file.

---

### 🟢 Option 1: Quick Deploy with Docker (**Recommended**)

1. **Clone this repository (optional: or just download the docker-compose.yml and .env.example)**
   ```bash
   git clone https://github.com/jack-jackhui/winning-cv.git
   cd winning-cv
   ```

2. **Create your `.env` file**
   ```bash
   cp env.example .env
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Edit `.env` and provide all necessary values (see [Configuration](#configuration) section below for details).

3. **(Optional, but recommended) Review and edit `docker-compose.yml`**

   Example `docker-compose.yml` (see repo for latest sample):
   ```yaml
   version: '3.8'
   services:
     winning-cv:
       image: ghcr.io/jack-jackhui/winning-cv:latest
       container_name: winning-cv
       restart: unless-stopped
       ports:
         - "13000:8501"  # Access UI on host port 13000
       volumes:
         - ./user_cv:/winning-cv/user_cv
         - cv_data:/winning-cv/customised_cv
         - ./.streamlit/secrets.toml:/winning-cv/.streamlit/secrets.toml  # Auth config
       env_file:
         - .env
   volumes:
     cv_data:
   ```

4. **Start the app**
   ```bash
   docker compose up -d
   ```

5. **Access the Web UI**
   - Open [http://localhost:13000](http://localhost:13000) in your browser.

6. **View logs (optional)**
   ```bash
   docker compose logs -f winning-cv
   ```

> **Note:**
> You must have a valid `.env` file with all required settings.
> All configuration (API keys, scraping URLs, notifications, etc.) is loaded from this file.

---

### 🧑‍💻 Option 2: Manual Local Installation (for Developers/Advanced Users)

1. **Clone the repository**
   ```bash
   git clone https://github.com/jack-jackhui/winning-cv.git
   cd winning-cv
   ```

2. **Create your `.env` file**
   ```bash
   cp env.example .env
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Fill in all required configuration (see details below).

3. **Install prerequisites**
   - **Python 3.10+** required
   - **Google Chrome** browser must be installed for scraping (see `.env` for path)
   - [uv](https://github.com/astral-sh/uv) for fast dependency install (or use pip)

4. **Install Python dependencies**
   ```bash
   uv pip install -r requirements.txt
   ```

5. **Download and install spaCy model**
   ```bash
   python -m spacy download en-core-web-sm
   python -c "import spacy; nlp = spacy.load('en_core_web_sm')"
   ```

6. **Set browser config in `.env`**
   For **macOS**:
   ```ini
   CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
   HEADLESS=false
   RUNNING_IN_DOCKER=false
   ```
   For **Windows**:
   ```ini
   CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
   HEADLESS=false
   RUNNING_IN_DOCKER=false
   ```

7. **Run the app locally**
   - Start Web UI:
     ```bash
     python webui_new.py
     ```
     Then go to [http://localhost:8501](http://localhost:8501)
   - Run CLI job:
     ```bash
     python main.py --user-email <your-email>
     ```

---

## ⚙️ Configuration
All configuration is managed via the `.env` file in your project root.
**Copy** `.env.example` to `.env` and fill in your settings.

<details>
<summary>Click to view a full <code>.env.example</code> template</summary>

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

# === Browser Configuration ===
CHROME_PATH="/path/to/chrome"      # Local development only
CHROMIUM_PATH="/usr/bin/chromium"  # Docker only
HEADLESS="true"                    # true for Docker, false for local
RUNNING_IN_DOCKER="false"          # Auto-set in Docker

# === Advanced Configuration ===
ADDITIONAL_SEARCH_TERM='AI IT (manager OR head OR director) "software engineering" leadership'
GOOGLE_SEARCH_TERM='head of IT or IT manager jobs near [Location] since last week'
```
</details>

---

### 🔑 Configuration Values Reference

- **BASE_CV_PATH**: Path to your base CV document (e.g. `user_cv/my_cv.docx`)
- **Airtable Credentials**: `AIRTABLE_PAT`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_ID`, `AIRTABLE_TABLE_ID_HISTORY`
- **Job Board URLs**:
  - `LINKEDIN_JOB_URL`: Your LinkedIn job search results URL (with preferred filters)
  - `SEEK_JOB_URL`: Your Seek job search results URL
- **Azure AI**: `AZURE_AI_ENDPOINT`, `AZURE_AI_API_KEY`, `AZURE_DEPLOYMENT`
- **Notification Channels**:
  - Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  - WeChat: `WECHAT_API_KEY`, `WECHAT_BOT_URL`
  - Email: `EMAIL_USER`, `EMAIL_PASSWORD`, `SMTP_SERVER`, `DEFAULT_FROM_EMAIL`, `DEFAULT_TO_EMAIL`
- **Job Search Parameters**:
  - `LOCATION` (e.g. "Melbourne,VIC")
  - `COUNTRY` (e.g. "australia")
  - `HOURS_OLD`, `RESULTS_WANTED`, `JOB_MATCH_THRESHOLD`, `MAX_JOBS_TO_SCRAPE`, `CHECK_INTERVAL_MIN`
- **Browser Configuration**:
  - For **Docker**: `CHROMIUM_PATH=/usr/bin/chromium`, `HEADLESS=true`, `RUNNING_IN_DOCKER=true`
  - For **Local**:  `CHROME_PATH`, `HEADLESS=false`, `RUNNING_IN_DOCKER=false`

> **Tip:**
> Most parameters have sensible defaults.
> For best results, review and update your job search URLs and notification channels.

---

### Authentication Secrets
| Key | Description | Example |
|-----|-------------|---------|
| `[connections.google]` | Google OAuth credentials | `client_id = "1234.apps.googleusercontent.com"` |
| `[email]` | Email restrictions | `allowed = ["@company.com"]` |

<details>
<summary>Full secrets.toml example</summary>

```toml
# .streamlit/secrets.toml
[connections]
[connections.google]
client_id = "your-google-client-id"
client_secret = "your-google-secret"
redirect_uri = "https://your-domain.com/oauth/callback"

[connections.github]
client_id = "your-github-client-id"
client_secret = "your-github-secret"

```
</details>

---

### 🛡️ Security & Best Practices
- **Never commit sensitive files**:
  ```bash
  echo ".env" >> .gitignore
  echo ".streamlit/secrets.toml" >> .gitignore
  ```
- Set strict file permissions:
  ```bash
  chmod 600 .env .streamlit/secrets.toml
  ```
- Rotate credentials regularly
- Use environment variables for CI/CD systems
- Review Streamlit's [security recommendations](https://docs.streamlit.io/develop/concepts/connections/authentication#security-considerations)
- Treat your API keys, tokens, and credentials as secrets
- Use named Docker volumes for persistent output storage
- For collaborative development, update `.env.example` if a new setting is introduced

---

## 🚦 Usage

**Web Dashboard**
- **Docker:** Visit [http://localhost:13000](http://localhost:13000)
- **Local:** Run `python webui_new.py` and open [http://localhost:8501](http://localhost:8501)

**Run CLI Job (Docker):**
```bash
docker compose run --rm job-runner
```
**Run CLI Job (Local):**
```bash
python main.py --user-email <your@email.com>
```

---

## Summary

- **Docker deployment:** Fast, portable, recommended for most users
- **Manual installation:** Full control, ideal for contributors and advanced users
- **All configuration:** Managed via `.env` (copy from `.env.example`)
- **Security:** Keep secrets out of version control

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
---
## Acknowledgments 🙏
This project stands on the shoulders of these amazing open-source technologies:

- **[JobSpy](https://github.com/speedyapply/JobSpy)** - Jobs scraper library for LinkedIn, Indeed, Glassdoor, Google, Bayt, & Naukri
- **[Docker](https://www.docker.com)** - Containerization magic
- **[Azure AI](https://azure.microsoft.com/en-us/products/ai-services)** - Core LLM capabilities
- **[spaCy](https://spacy.io)** - NLP processing backbone
- **[Ollama](https://ollama.ai)** - Local LLM integration (upcoming)
- **[LinkedIn/Seek](https://www.linkedin.com/)** - Job data sources

*Special thanks to all open-source maintainers and contributors who make projects like this possible.*

---
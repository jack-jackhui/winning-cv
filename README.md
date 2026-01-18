<div align="center">
<h1 align="center">Winning CV - Job Matching & CV Tailoring Platform</h1>

<p align="center">
  <strong>Stop sending generic resumes. Get tailored CVs for every opportunity.</strong>
</p>

<p align="center">
  <a href="https://winning-cv.jackhui.com.au">Try It Free</a> |
  <a href="#quick-start">Quick Start</a> |
  <a href="#features">Features</a> |
  <a href="README-zh.md">简体中文</a>
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

## Try It Now — No Installation Required

**Use Winning CV instantly at:** [https://winning-cv.jackhui.com.au](https://winning-cv.jackhui.com.au)

- **Zero setup** — just sign in and start
- **Free to use** (fair use limits apply)
- **All features available** via the web

> **Tip:** Try the hosted version first to see the full capabilities before setting up locally!

---

## What is Winning CV?

Winning CV is an open-source application that transforms how you apply for jobs. Instead of manually tailoring resumes for each position, our intelligent system:

1. **Scans job platforms** — LinkedIn, Seek, Indeed, Glassdoor, and Google Jobs
2. **Analyzes every listing** against your base CV using semantic NLP
3. **Scores compatibility** (0-10) so you know where to focus
4. **Generates tailored resumes** optimized for each specific role
5. **Notifies you instantly** via Email, Telegram, or WeChat when great matches appear

**The result?** Less time on applications, higher interview rates.

---

## Features

### Smart Job Aggregation
- Real-time crawling of LinkedIn, Seek, Indeed, Glassdoor, Google Jobs
- Advanced filtering by location, keywords, and job parameters
- Automatic duplicate detection and priority sorting
- LinkedIn cookie health monitoring for reliable scraping

### CV-to-Job Matching Engine
- Semantic analysis of job descriptions vs. your base CV using spaCy NLP
- Compatibility scoring system (0-10 scale)
- CV-JD fit analysis with detailed breakdown
- Skills gap identification and recommendations

### Automated CV Generation
- Context-aware resume customization via Azure AI
- Position-specific keyword optimization
- Format preservation (PDF/DOCX)
- Achievement highlighting based on job requirements

### CV Version Library
- Automatic versioning for every generated CV
- MinIO-powered secure storage with presigned URLs
- Category detection and custom tagging
- Fork, archive, restore, and delete versions
- Usage and response tracking with analytics
- Select from library before job search

### Multi-Channel Notifications
- **Email** — SMTP-based notifications with customizable templates
- **Telegram** — Instant alerts via bot with your Chat ID
- **WeChat** — Direct messaging via custom WeChat API integration
- Test notifications from profile settings
- Detailed job information in every notification

### Modern Dashboard
- **Interactive Stats** — Total matches, CVs generated, average scores
- **Job Match Browser** — Filter, sort, and explore matched jobs
- **CV Analytics** — Track which CV versions get the best response rates
- **Performance Metrics** — Monitor your job search effectiveness

### Authentication & Security
- Microsoft OAuth integration
- Token-based API authentication
- Secure session management
- Per-user notification preferences

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, Tailwind CSS, HeroUI |
| Backend | FastAPI, Python 3.10+ |
| Admin UI | Streamlit with OAuth |
| Storage | MinIO (S3-compatible), Airtable |
| NLP | spaCy with en-core-web-sm |
| Containerization | Docker, Docker Compose |

---

## Quick Start

### Option 1: Docker (Recommended)

The fastest way to get started with all services running:

```bash
# Clone the repository
git clone https://github.com/jack-jackhui/winning-cv.git
cd winning-cv

# Create configuration files
cp env.example .env
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Edit .env with your API keys and settings (see Configuration section)

# Start all services
docker compose up -d
```

**Access points:**
- **React Frontend:** http://localhost:13000
- **FastAPI Backend:** http://localhost:8000
- **API Documentation:** http://localhost:8000/api/docs
- **MinIO Console:** http://localhost:9001

### Option 2: Local Development

For contributors and developers who want full control:

```bash
# Clone and setup
git clone https://github.com/jack-jackhui/winning-cv.git
cd winning-cv

# Create configuration
cp env.example .env
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Install Python dependencies (requires Python 3.10+)
pip install uv  # or: brew install uv
uv pip install -r requirements.txt

# Install spaCy language model
python -m spacy download en-core-web-sm

# Configure browser path in .env
# macOS: CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Windows: CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
# Set: HEADLESS=false and RUNNING_IN_DOCKER=false
```

**Run the services:**

```bash
# Terminal 1: FastAPI Backend
python run_api.py
# API at http://localhost:8000, Docs at http://localhost:8000/api/docs

# Terminal 2: React Frontend (for development)
cd frontend && npm install && npm run dev
# Frontend at http://localhost:3000

# Terminal 3: Streamlit Admin UI
python webui_new.py
# Admin UI at http://localhost:8501

# Or run CLI job search
python main.py --user-email your@email.com
```

---

## How It Works

### Web UI Workflow

1. **Sign In** — Use Microsoft OAuth
2. **Configure Search** — Enter job keywords, location, and preferences
3. **Select CV** — Choose from your CV library or upload a new one
4. **Run Search** — System scrapes jobs and scores matches in real-time
5. **Review Matches** — Browse jobs with compatibility scores
6. **Download CVs** — Get tailored resumes optimized for each role
7. **Manage Library** — Track all versions, see analytics, and optimize your approach

### CLI Workflow

```bash
# Set job search URLs in .env
LINKEDIN_JOB_URL=https://linkedin.com/jobs/search?keywords=...
SEEK_JOB_URL=https://seek.com.au/...

# Run the job processor
python main.py --user-email your@email.com
```

Jobs are analyzed, CVs generated, and notifications sent automatically.

---

## Configuration

All settings are managed via `.env` file. Copy `env.example` and configure:

<details>
<summary><strong>Click to expand full configuration reference</strong></summary>

```ini
# === Base CV ===
BASE_CV_PATH=user_cv/my_resume.docx

# === Airtable (Data Storage) ===
AIRTABLE_PAT=your-personal-access-token
AIRTABLE_BASE_ID=your-base-id
AIRTABLE_TABLE_ID=main-jobs-table-id
AIRTABLE_TABLE_ID_HISTORY=history-table-id
AIRTABLE_TABLE_ID_USER_CONFIGS=user-configs-table-id
AIRTABLE_TABLE_ID_CV_VERSIONS=cv-versions-table-id

# === MinIO (CV File Storage) ===
MINIO_ENDPOINT=localhost:9000       # or minio:9000 in Docker
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_BUCKET=winningcv-cvs

# === Job Board URLs (CLI mode) ===
LINKEDIN_JOB_URL=https://linkedin.com/jobs/search?...
SEEK_JOB_URL=https://seek.com.au/...

# === Azure AI ===
AZURE_AI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_AI_API_KEY=your-api-key
AZURE_DEPLOYMENT=deployment-name

# === Notifications ===
# Email
EMAIL_USER=your@email.com
EMAIL_PASSWORD=your-password
SMTP_SERVER=smtp.server.com
DEFAULT_FROM_EMAIL=noreply@example.com
DEFAULT_TO_EMAIL=your@email.com

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# WeChat (Direct API)
WECHAT_API_URL=https://your-wechat-api.com
WECHAT_API_KEY=your-api-key

# === Search Parameters ===
LOCATION=Melbourne,VIC
COUNTRY=Australia
HOURS_OLD=168          # Jobs from last 7 days
RESULTS_WANTED=10      # Jobs per platform
JOB_MATCH_THRESHOLD=7  # Minimum match score (0-10)
MAX_JOBS_TO_SCRAPE=50

# === Browser (Local Development) ===
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HEADLESS=false
RUNNING_IN_DOCKER=false
```

</details>

### Authentication Setup

Configure OAuth providers in `.streamlit/secrets.toml`:

```toml
[connections.google]
client_id = "your-google-client-id"
client_secret = "your-google-secret"
redirect_uri = "https://your-domain.com/oauth/callback"

[connections.microsoft]
client_id = "your-microsoft-client-id"
client_secret = "your-microsoft-secret"
```

See [Streamlit Authentication Docs](https://docs.streamlit.io/develop/concepts/connections/authentication) for setup guides.

---

## Architecture

```
winning-cv/
├── frontend/              # React + Vite + Tailwind dashboard
│   └── src/
│       ├── pages/         # Dashboard, CVLibrary, Analytics, Profile, etc.
│       ├── components/    # Reusable UI components
│       ├── context/       # Auth context
│       └── services/      # API client
├── api/                   # FastAPI REST backend
│   ├── routes/            # auth, cv, cv_versions, jobs, profile
│   ├── middleware/        # Authentication middleware
│   └── schemas/           # Pydantic models
├── job_processing/        # Core matching engine
├── job_sources/           # Platform scrapers (LinkedIn, Seek, etc.)
│   └── linkedin_cookie_health.py  # Cookie monitoring
├── data_store/            # Airtable + CV version manager
├── cv/                    # CV parsing & generation
├── utils/                 # MinIO storage, notifications, logging
├── scheduler/             # APScheduler background jobs
├── webui_new.py           # Streamlit admin application
├── main.py                # CLI interface
└── run_api.py             # FastAPI server entry point
```

### Services (Docker Compose)

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 13000 | React SPA via Nginx |
| `api` | 8000 | FastAPI REST backend |
| `job-runner` | - | CLI batch processor |
| `minio` | 9000/9001 | S3-compatible storage |

---

## API Reference

The FastAPI backend provides a complete REST API:

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/me` | GET | Get auth status |
| `/api/v1/auth/user` | GET | Get user info |
| `/api/v1/auth/login-url` | GET | Get OAuth login URL |
| `/api/v1/auth/logout` | POST | Logout |

### Jobs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/jobs/config` | GET | Get job search config |
| `/api/v1/jobs/config` | POST | Save job search config |
| `/api/v1/jobs/search` | POST | Start job search |
| `/api/v1/jobs/search/{task_id}/status` | GET | Get search status |
| `/api/v1/jobs/results` | GET | List matched jobs |
| `/api/v1/jobs/linkedin/health` | GET | LinkedIn cookie health |

### CV Versions
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/cv/versions` | GET | List CV versions |
| `/api/v1/cv/versions` | POST | Create CV version |
| `/api/v1/cv/versions/{id}` | GET | Get version details |
| `/api/v1/cv/versions/{id}` | PATCH | Update version |
| `/api/v1/cv/versions/{id}` | DELETE | Delete version |
| `/api/v1/cv/versions/{id}/download` | GET | Get download URL |
| `/api/v1/cv/versions/{id}/fork` | POST | Fork version |
| `/api/v1/cv/versions/analytics/summary` | GET | Get analytics |

### Profile & Notifications
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/profile/notifications` | GET | Get notification preferences |
| `/api/v1/profile/notifications` | PUT | Update preferences |
| `/api/v1/profile/notifications/test` | POST | Send test notification |

Full interactive docs at: `http://localhost:8000/api/docs`

---

## Security Best Practices

```bash
# Never commit secrets
echo ".env" >> .gitignore
echo ".streamlit/secrets.toml" >> .gitignore

# Restrict file permissions
chmod 600 .env .streamlit/secrets.toml
```

- Rotate credentials regularly
- Use environment variables in CI/CD
- Keep API keys and tokens secure
- Review [Streamlit security recommendations](https://docs.streamlit.io/develop/concepts/connections/authentication#security-considerations)

---

## Roadmap

- [ ] Local LLM support with Ollama
- [ ] Browser extension for one-click applications
- [ ] Salary negotiation assistant
- [ ] Application success analytics dashboard
- [ ] Mobile app (iOS/Android)
- [ ] More job platforms integration
- [ ] Community plugin marketplace

---

## Contributing

We welcome contributions! Here's how you can help:

- **Report bugs** via [GitHub Issues](https://github.com/jack-jackhui/winning-cv/issues)
- **Submit PRs** for features and fixes
- **Develop platform connectors** for new job sites
- **Improve documentation** and tutorials
- **Share your success stories**

Please read our [Contribution Guidelines](CONTRIBUTING.md) before submitting PRs.

---

## License

Released under the [MIT License](LICENSE).

---

## Disclaimer

- Job data comes from third-party platforms
- Users must comply with each platform's Terms of Service
- Always review generated CVs before submission
- Not affiliated with LinkedIn, Seek, Indeed, or other job platforms

---

<div align="center">

**Transform Your Job Search Today**

[Try Winning CV Free](https://winning-cv.jackhui.com.au) | [View Documentation](https://github.com/jack-jackhui/winning-cv)

**Star this repo to support development!**

</div>

---

## Acknowledgments

Built with these amazing open-source technologies:

- **[JobSpy](https://github.com/speedyapply/JobSpy)** — Multi-platform job scraping
- **[FastAPI](https://fastapi.tiangolo.com)** — Modern Python web framework
- **[React](https://react.dev)** — UI component library
- **[HeroUI](https://heroui.com)** — React component library
- **[Streamlit](https://streamlit.io)** — Rapid dashboard development
- **[MinIO](https://min.io)** — S3-compatible object storage
- **[spaCy](https://spacy.io)** — Industrial NLP
- **[Docker](https://docker.com)** — Containerization

*Special thanks to all open-source maintainers and contributors who make projects like this possible.*

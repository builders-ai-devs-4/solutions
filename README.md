# AI Devs 4 — Solutions

Personal solutions repository for the **AI Devs 4** course — 20 exercises across 4 seasons, building progressively more complex LLM-powered agents using LangChain and LangGraph.

---

## Seasons & Episodes

### Season 1 — Foundations

| Episode | Focus | Key Concepts |
| ------- | ----- | ------------ |
| S01E01 | Data filtering & LLM classification | CSV processing, structured output, job-tag classification |
| S01E02 | ReAct investigation agent | LangGraph ReAct loop, location tracking, tool use |
| S01E03 | FastAPI + agent backend | Web API server, pytest test suite, start scripts |
| S01E04 | Asset collection & form filling | Agent memory, markdown index ingestion |
| S01E05 | Action-based agent workflow | Custom actions, helpers, multi-step execution |

### Season 2 — Multi-Agent Systems

| Episode | Focus | Key Concepts |
| ------- | ----- | ------------ |
| S02E01 | Single supervisor agent | Logging setup, model configuration, request handling |
| S02E02 | Hierarchical multi-agent | Supervisor + sub-agents, OCR (pytesseract, OpenCV) |
| S02E03 | Enhanced logging & filtering | Log filters, structured agent coordination |
| S02E04 | Seeker agent pattern | Specialised retrieval agent architecture |
| S02E05 | Seeker agent with scripts | Extended seeker with auxiliary script utilities |

### Season 3 — Data Persistence & APIs

| Episode | Focus | Key Concepts |
| ------- | ----- | ------------ |
| S03E01 | Database + validation | DuckDB integration, caching, result validation |
| S03E02 | Database-driven agent | Seeker agent with DuckDB, module architecture |
| S03E03 | Enhanced database agent | Extended DB tooling, improved seeker |
| S03E04 | Full-stack API + task server | FastAPI app, background processor, DuckDB, shared libs |
| S03E05 | Supervisor + sub-agents + DB | Hierarchical agents with persistent DuckDB storage |

### Season 4 — Spatial Reasoning & Advanced Search

| Episode | Focus | Key Concepts |
| ------- | ----- | ------------ |
| S04E01 | Map-based agent | OKO location client, LangFuse observability |
| S04E02 | Map navigation | Map reset / manipulation, supervisor navigation agent |
| S04E03 | Path finding & map utilities | Async map utils, spatial reasoning, BeautifulSoup |
| S04E04 | Full-text search | SQLite FTS indexing, database-backed retrieval |
| S04E05 | Combined map + search | Map navigation + FTS search, most complex S04 task |

---

## Technology Stack

| Category | Libraries / Tools |
| -------- | ----------------- |
| LLM framework | LangChain 1.2.14, LangGraph 1.1.4 |
| LLM providers | OpenAI (GPT-4o), OpenRouter |
| Agent pattern | ReAct (Reason-Act) via LangGraph |
| Structured output | Pydantic v2 |
| Web framework | FastAPI + Uvicorn (S01E03, S03E04) |
| Databases | DuckDB (S03), SQLite FTS (S04E04) |
| Observability | LangFuse 0.7.24, OpenTelemetry |
| Data processing | BeautifulSoup4, html-to-markdown, Tesseract OCR |
| Testing | pytest + coverage |

---

## Project Structure

```text
solutions/
├── s01e01/ … s04e05/   # 20 exercise solutions (Season × Episode)
├── libs/               # Shared utilities used across episodes
├── bootstraps/         # Task scaffolding templates
├── logs/               # Centralised agent logs
└── requirements-task.txt
```

Each exercise folder follows a consistent layout:

```text
s0xexx/
├── task.py                  # Main entry point
├── readme_task.md           # Task description
├── requirements.txt
├── .env                     # Local secrets (git-ignored)
├── .env-example             # Required env var template
├── agents.py / supervisor_agent.py
├── tools.py
├── subagents.py             # Present from S02 onward
├── prompts/                 # System/user prompt markdown files
└── modules/                 # Reusable in-episode modules (S02+)
```

---

## Shared Libraries (`libs/`)

| Module | Purpose |
| ------ | ------- |
| `central_client.py` | POST to central grading server, scan flags in responses |
| `database.py` | DuckDB abstraction — load CSV/JSON into named tables |
| `filetype_detect.py` | File type detection by extension and MIME type |
| `generic_helpers.py` | URL helpers, file I/O, base64 read utilities |
| `logger.py` | Standard logger with file output |
| `loggers.py` | LangChain callback handler wired to LangFuse |
| `tiktoken.py` | Model-specific token counting |
| `tomarkdown.py` | HTML → Markdown conversion for web content |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements-task.txt
```

### 2. Configure environment variables

Each episode ships with an `.env-example`. Copy it and fill in your keys:

```bash
cp s01e01/.env-example s01e01/.env
```

Common variables across episodes:

```env
AI_DEVS_SECRET=          # Course API secret
OPENAI_API_KEY=          # OpenAI key
OPENROUTER_API_KEY=      # OpenRouter key (optional)
HUB_URL=                 # Course hub endpoint
TASK=                    # Current task slug (e.g. s02e01)
SOLUTION_URL=            # Where to submit the answer
SOURCE_URL=              # Input data URL (task-specific)
DATA_FOLDER=.data

# Observability (optional)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

### 3. Run a task

```bash
cd s01e02
python task.py
```

Episodes with a web server (S01E03, S03E04):

```bash
cd s01e03
./start.sh        # or start.ps1 on Windows
```

### 4. Bootstrap a new task

```bash
cd bootstraps
python bootstrap_task.py s05e01
```

---

## Running Tests

```bash
pytest --cov=src --cov-report=term-missing
```

Test suites are present in S01E03 and S03E04.

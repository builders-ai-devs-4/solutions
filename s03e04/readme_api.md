# Install venv

```bash
python -m venv venv
python -m pip install --upgrade pip
```

## Install dependencies

```bash
pip install -U langchain langchain-openai pydantic langgraph langchain-openrouter
pip install langchain-community
pip install fastapi
pip install "uvicorn[standard]"
pip install httpx
pip install python-dotenv
pip install tiktoken
pip install html-to-markdown
pip install duckdb
pip install langfuse
```

## Install dependencies dev

```bash
pip install -U langchain langchain-openai pydantic langgraph langchain-openrouter
pip install langchain-community
pip install fastapi
pip install "uvicorn[standard]"
pip install pytest pytest-asyncio httpx
pip install python-dotenv
pip install tiktoken
pip install html-to-markdown
pip install duckdb
pip install langfuse
```

## Activate venv on linux

```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

## Install deps from requirements

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Start app

```bash
uvicorn src.main:app --reload
```

## Bootstraps

``` bash
# Development environment
bash start.sh
bash start.sh --reload
# Production environment
APP_ENV=production bash start.sh
```

```powershell
# Development environment
.\start.ps1
.\start.ps1 -Reload
# Production environment
$env:APP_ENV="production"; .\start.ps1
```

## Tests run

```bash
# Start the server (in a separate terminal)
python scripts/start.py --reload

# Run all tests
python scripts/test.py

# Run a specific test
python scripts/test.py -- -k test_health_check

# Stop on first failure
python scripts/test.py -- -x

# Stop on first failure with short traceback
python scripts/test.py -- -x --tb=short

# Show help
python scripts/test.py -h

# Terminal report
python scripts/test.py -- --cov=src

# Terminal report with uncovered lines
python scripts/test.py -- --cov=src --cov-report=term-missing

# HTML report (most readable, opens in browser)
python scripts/test.py -- --cov=src --cov-report=html

# Both at once
python scripts/test.py -- --cov=src --cov-report=term-missing --cov-report=html
```

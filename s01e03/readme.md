# Install dependencies

```bash
python -m venv venv
python -m pip install --upgrade pip
pip install -U langchain langchain-openai pydantic langgraph
pip install fastapi
pip install "uvicorn[standard]"
pip install pytest pytest-asyncio httpx
```

## Activate on linux

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
```
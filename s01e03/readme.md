# Install dependencies

```bash
python -m venv venv
python.exe -m pip install --upgrade pip
pip install -U langchain langchain-openai pydantic langgraph
pip install fastapi
pip install "uvicorn[standard]"
pip install pytest pytest-asyncio httpx
```

## Install deps from requirements

```bash
pip install -r requirements.tx
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

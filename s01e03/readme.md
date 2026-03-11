# Install dependencies

```bash
python -m venv venv
python.exe -m pip install --upgrade pip
pip install -U langchain langchain-openai pydantic langgraph
pip install fastapi
pip install "uvicorn[standard]"
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


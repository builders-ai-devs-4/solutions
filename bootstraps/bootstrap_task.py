from pathlib import Path
import base64, ast

output_dir = Path("/root/output")
output_dir.mkdir(parents=True, exist_ok=True)

# ── Szablony plików ───────────────────────────────────────────────────────────

def enc(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")

T = {}

T[".env"] = enc("""\
AI_DEVS_SECRET=twoj-klucz
OPENAI_API_KEY=
OPENROUTER_API_KEY=

TASK_NAME=TASK_NAME_PLACEHOLDER
SOLUTION_URL=https://hub.ag3nts.org/report
DATA_FOLDER=.data

# SOURCE_URL1=
# SOURCE_URL2=
""")

T["task.py"] = enc("""\
import os, sys
from dotenv import load_dotenv
from string import Template
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from libs.loggers import agent_logger

load_dotenv()
AI_DEVS_SECRET = os.getenv("AI_DEVS_SECRET")
SOLUTION_URL   = os.getenv("SOLUTION_URL")
DATA_FOLDER    = os.getenv("DATA_FOLDER")
TASK_NAME      = os.getenv("TASK_NAME")

current_folder     = Path(__file__)
parent_folder_path = current_folder.parent
task_data_folder   = parent_folder_path / DATA_FOLDER / TASK_NAME
task_data_folder.mkdir(parents=True, exist_ok=True)

os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"]    = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"]      = str(parent_folder_path / DATA_FOLDER)
# TODO: os.environ["SOURCE_URL1"] = os.getenv("SOURCE_URL1")

from seeker_agent import SEEKER_CONFIG, seeker

seeker_user_template = (
    parent_folder_path / "prompts" / "seeker_user.md"
).read_text(encoding="utf-8")

seeker_user = Template(seeker_user_template).substitute(
    SOLUTION_URL=SOLUTION_URL,
    # TODO: dodaj zmienne podstawiane do promptu
)

if __name__ == "__main__":
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    result = seeker.invoke(
        {"messages": [{"role": "user", "content": seeker_user}]},
        config=SEEKER_CONFIG,
    )
    agent_logger.info(f"[task] {result['messages'][-1].content}")
""")

T["seeker_agent.py"] = enc("""\
import os, sys
from pathlib import Path
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openrouter import ChatOpenRouter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from libs.loggers import agent_logger, LoggerCallbackHandler
from tools import _RECURSION_LIMIT  # TODO: zaimportuj narzędzia

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]

seeker_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_system.md"
).read_text(encoding="utf-8")

SEEKER_CONFIG = {
    "configurable": {"thread_id": f"{TASK_NAME}-seeker"},
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

seeker_model = ChatOpenRouter(
    model="google/gemini-2.5-pro-preview-03-25",  # TODO: zmień model
    temperature=0,
)

seeker = create_agent(
    model=seeker_model,
    tools=[
        # TODO: dodaj narzędzia, np.:
        # scan_flag,
        # send_answer,
    ],
    system_prompt=seeker_system,
    name="seeker",
    checkpointer=InMemorySaver(),
)
""")

T["tools.py"] = enc("""\
import os, re, sys, json
from typing import Optional
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from libs.loggers import agent_logger
from libs.central_client import _post_to_central

AI_DEVS_SECRET        = os.environ["AI_DEVS_SECRET"]
TASK_NAME             = os.environ["TASK_NAME"]
SOLUTION_URL          = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH    = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

FLAG_RE = re.compile(r"\\{FLG:[^}]+\\}")
MAX_TOOL_ITERATIONS = 15
_RECURSION_LIMIT    = MAX_TOOL_ITERATIONS * 10 + 2  # 152


# -- Input schemas -------------------------------------------------------------

class SendAnswerInput(BaseModel):
    answer: str = Field(description="TODO: opisz czego oczekuje centrala")


# -- Tools ---------------------------------------------------------------------

@tool
def scan_flag(text: str) -> Optional[str]:
    "Search for a success flag {FLG:...} in text. Call after every server response."
    match = FLAG_RE.search(text)
    if match:
        agent_logger.info(f"[FLAG FOUND] {match.group(0)}")
        return match.group(0)
    agent_logger.info(f"[scan_flag] no flag (len={len(text)})")
    return None


@tool(args_schema=SendAnswerInput, response_format="content_and_artifact")
def send_answer(answer: str) -> tuple[str, dict]:
    "Submit the final answer to central verification endpoint."
    return _post_to_central(answer)  # TODO: dostosuj strukturę, np. {"key": answer}


# TODO: Dodaj narzędzia specyficzne dla zadania
""")

T["prompts/seeker_system.md"] = enc("""\
You are an autonomous agent solving a task from the AI_Devs4 course.

## Goal
TODO: Opisz cel zadania

## Strategy
TODO: Opisz strategię krok po kroku:
1. ...
2. ...
3. ...

## Rules
- Always call scan_flag after receiving a server response
- Submit the answer only when you are confident it is correct
- Analyze server errors and adjust your approach

## Output format
TODO: Opisz oczekiwany format odpowiedzi
""")

T["prompts/seeker_user.md"] = enc("""\
TODO: Opisz zadanie dla agenta.

Submit your answer to: $SOLUTION_URL

Start by TODO: opisz pierwszy krok.
""")

T["modules/__init__.py"] = enc("")

T["modules/models.py"] = enc("""\
from pydantic import BaseModel, Field
from typing import Optional


# TODO: Dodaj modele Pydantic specyficzne dla zadania
#
# Przyklad:
# class TaskResult(BaseModel):
#     answer: str
#     confidence: float = Field(ge=0.0, le=1.0)
""")

# ── Buduj skrypt ──────────────────────────────────────────────────────────────

lines = [
    "#!/usr/bin/env python3",
    '"""bootstrap_task.py - generuje szkielet nowego zadania AI_Devs4',
    "Uzycie: python bootstrap_task.py s01e03",
    '"""',
    "import sys, os, re, base64",
    "from pathlib import Path",
    "",
    'TASKS_ROOT = Path(__file__).parent / "solutions"',
    "",
    "# Szablony plikow zakodowane w base64",
    "_T: dict[str, str] = {",
]

for dest, b64 in T.items():
    lines.append(f"    {dest!r}: {b64!r},")

lines += [
    "}",
    "",
    "",
    "def _render(content: str, task_name: str) -> str:",
    '    return content.replace("TASK_NAME_PLACEHOLDER", task_name)',
    "",
    "",
    "def generate(task_name: str) -> None:",
    "    task_dir = TASKS_ROOT / task_name",
    "    if task_dir.exists():",
    '        print(f"[ERROR] Folder already exists: {task_dir}"); sys.exit(1)',
    "    task_dir.mkdir(parents=True)",
    '    print(f"[bootstrap] Creating: {task_name} -> {task_dir}")',
    "    for rel_path, b64 in _T.items():",
    '        raw      = base64.b64decode(b64).decode("utf-8")',
    "        rendered = _render(raw, task_name)",
    "        fpath    = task_dir / rel_path",
    "        fpath.parent.mkdir(parents=True, exist_ok=True)",
    '        fpath.write_text(rendered, encoding="utf-8")',
    '        print(f"  ok {rel_path}")',
    "    print(f\"\"\"",
    "[bootstrap] Done! Next steps:",
    "  1. cd solutions/{task_name}",
    "  2. .env                   -> fill in keys and SOURCE_URLs",
    "  3. prompts/seeker_system  -> describe goal & strategy",
    "  4. prompts/seeker_user    -> write the user message",
    "  5. tools.py               -> add task-specific tools + fix SendAnswerInput",
    "  6. seeker_agent.py        -> register tools, pick model",
    "  7. python task.py",
    '""")',
    "",
    "",
    'if __name__ == "__main__":',
    "    if len(sys.argv) != 2:",
    '        print("Usage: python bootstrap_task.py s01e03"); sys.exit(1)',
    "    name = sys.argv[1].strip().lower()",
    '    if not re.match(r"^s0[1-5]e0[1-5]$", name):',
    '        print(f"[ERROR] Invalid: {name!r}. Expected s0Xe0Y, X/Y in 1-5")',
    "        sys.exit(1)",
    "    generate(name)",
]

script = "\n".join(lines)

# Walidacja składni
ast.parse(script)
print("Skladnia: OK")

out = output_dir / "bootstrap_task.py"
out.write_text(script, encoding="utf-8")
print(f"Zapisano: {out.name}  {out.stat().st_size / 1024:.1f} KB")

# Szybki test — czy b64 dla tools.py rozkodowuje się poprawnie
tools_raw = base64.b64decode(T["tools.py"]).decode("utf-8")
assert "_post_to_central" in tools_raw
assert "scan_flag" in tools_raw
assert "send_answer" in tools_raw
print("Weryfikacja zawartosci tools.py: OK")
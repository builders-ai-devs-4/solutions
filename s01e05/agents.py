import os

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import railway_action
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

SYSTEM_PROMPT = """
You are a railway API client. Activate route X-01 by calling actions in this exact order:
1. reconfigure  (route=X-01)
2. getstatus    (route=X-01)  — check current status
3. setstatus    (route=X-01, value=RTOPEN)
4. save         (route=X-01)

After every response check if it contains a flag in format {FLG:...}.
If you see the flag, report it immediately and stop.
Do NOT skip or reorder steps.
"""

railway_agent = create_agent(
    model="openai:gpt-5-mini",
    tools=[railway_action],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=InMemorySaver(),
)

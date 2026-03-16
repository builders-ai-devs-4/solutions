from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from tools import get_file_list, read_file  # atomowe narzędzia

llm = ChatOpenAI(model="gpt-4o")

# --- Subagenci ---

file_agent = create_agent(
    llm,
    tools=[get_file_list, read_file],
    system_prompt="Jesteś ekspertem od operacji na plikach. ...",
    name="file_agent",  # ważne dla debugowania w LangSmith
)

# Subagent jako tool dla supervisora
@tool("file_specialist", description="Deleguj zadania związane z plikami.")
def call_file_agent(task: str) -> str:
    result = file_agent.invoke({"messages": [{"role": "user", "content": task}]})
    return result["messages"][-1].content

# --- Supervisor ---

supervisor = create_agent(
    llm,
    tools=[call_file_agent, ...],  # subagenci jako tools
    system_prompt="Jesteś supervisorem. Rozkładasz zadania na specjalistów.",
    name="supervisor",
)
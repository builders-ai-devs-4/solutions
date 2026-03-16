from langchain.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")

# Subagent jako tool
@tool("research_agent", description="Badaj tematy i zwracaj fakty")
def call_research(query: str):
    subagent = create_agent(llm, tools=[...])  # Dodaj narzędzia subagenta
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# Supervisor
supervisor = create_agent(llm, tools=[call_research])
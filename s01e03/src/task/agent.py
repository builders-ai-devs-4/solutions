import asyncio
import os
from pathlib import Path
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from task.chat_history import get_session_lock, get_session_history
from task.tools import check_package, redirect_package

memory = InMemorySaver()

PARENT_FOLDER_PATH = Path(os.getenv("PARENT_FOLDER_PATH"))

agent = create_agent(
    model="openai:gpt-5-mini",
    tools=[check_package, redirect_package],
    system_prompt="Jesteś asystentem operatora paczek.",
    checkpointer=memory,
)

async def run_agent(session_id: str, user_message: str) -> str:
    async with get_session_lock(session_id):
        config = {"configurable": {"thread_id": session_id}}

        result = await asyncio.to_thread(
            agent.invoke,
            {"messages": [HumanMessage(content=user_message)]},
            config=config,
        )

        answer = result["messages"][-1].content

        file_message_history = get_session_history(session_id)
        file_message_history.add_user_message(user_message)
        file_message_history.add_ai_message(answer)

        return answer
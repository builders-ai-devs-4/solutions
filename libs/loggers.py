import os
import sys
import logging
from pathlib import Path
from langchain_core.callbacks import BaseCallbackHandler

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs"))
from libs.logger import get_logger


def _log_dir() -> Path:
    base = os.environ.get("DATA_FOLDER_PATH", ".")
    return Path(base) / "logs"


agent_logger = get_logger("agent", log_dir=_log_dir(), log_stem="agent")
# api_logger   = get_logger("api",   log_dir=_log_dir(), log_stem="api")


class LoggerCallbackHandler(BaseCallbackHandler):
    def __init__(self, logger: logging.Logger):
        self.log = logger

    def on_chat_model_start(self, serialized, messages, **kwargs):
        model = (serialized or {}).get("name", "unknown")
        # log only the last human message for context (truncated)
        last_msg = ""
        if messages and messages[-1]:
            raw = messages[-1][-1] if isinstance(messages[-1], list) else messages[-1]
            content = getattr(raw, "content", str(raw))
            last_msg = content[:120].replace("\n", " ")
        self.log.info(f"[LLM start]: model={model} | prompt=…{last_msg}…")

    def on_llm_end(self, response, **kwargs):
        usage = {}
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
        if usage:
            self.log.info(f"[LLM done]: tokens={usage}")
        else:
            self.log.info("[LLM done]")

    def on_tool_start(self, serialized, input_str, **kwargs):
        self.log.info(f"[Tool call]: {serialized['name']} | input: {input_str}")

    def on_tool_end(self, output, **kwargs):
        self.log.info(f"[Tool result]: {output}")

    def on_tool_error(self, error, **kwargs):
        self.log.warning(f"[Tool error]: {error}")

    def on_agent_action(self, action, **kwargs):
        self.log.info(f"[Agent action]: {action.tool} | {action.tool_input}")

    def on_agent_finish(self, finish, **kwargs):
        self.log.info(f"[Agent finished]: {finish.return_values}")
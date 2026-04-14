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
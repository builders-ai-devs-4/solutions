# User Prompt: Initialization of Diagnostic Procedure

I am initiating the diagnostic procedure. Your primary objective is to analyze the system logs
from the current shift and identify the root cause of the power plant failure.

## Operational Context (External Variables):
* **LIMIT_TOKENOW:** {TOKEN_LIMIT}
* **FAILURE_LOG_URL:** {FAILURE_LOG_URL}
* **SOLUTION_URL:** {SOLUTION_URL}
* **TASK_DATA_FOLDER_PATH:** {TASK_DATA_FOLDER_PATH}

## Required operational steps:

1. **Initialization and File Management (CRITICAL):**
   - Check the current system date and time.
   - If the time is 00:00 (or the date has changed since the last check), previously downloaded data is stale — you must download a new log file from `FAILURE_LOG_URL`.
   - Always use available tools to extract the base filename (FILE_NAME) from the `FAILURE_LOG_URL`.
   - The day's log file must always be saved under `TASK_DATA_FOLDER_PATH` using the filename format: `FILE_NAME_YYYY-MM-DD.log` (using the current date). Verify whether such a file already exists before downloading.
2. **First iteration (General phase):** Delegate to the Seeker agent the task of extracting key events marked as errors. Pass the resulting lines to the Compressor agent for formatting and maximal compression. Inform the Compressor of the strict token limit `LIMIT_TOKENOW`.
3. **Reporting:** Send the compressed log package to `SOLUTION_URL` and analyze the feedback received.
4. **Diagnostic loop (Detailed iterations):** Continue iteratively. Use feedback from Central to instruct the Seeker agent to retrieve missing data about specific subsystems. Ask the Compressor agent to recompress the updated log set, strictly ensuring the result never exceeds `LIMIT_TOKENOW` before the next submission.

## Critical constraints:
* You are strictly forbidden from directly reading raw log files into your own memory context.
* All operations for searching, filtering, and parsing text from the file must be delegated to sub-agents (Seeker and Compressor).

The procedure ends only when Central's response contains an authorization flag in the format `{FLG:...}`. Proceed to execute the task.
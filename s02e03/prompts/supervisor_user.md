# User Prompt: Diagnostic Procedure Initialization

I am initiating the diagnostic procedure. Your overarching goal is to analyze 
the system logs from the current shift and identify the root cause of the 
power plant failure.

## Operational Context (External Variables):
* **TOKEN_LIMIT:** $TOKEN_LIMIT
* **FAILURE_LOG_URL:** $FAILURE_LOG_URL
* **SOLUTION_URL:** $SOLUTION_URL
* **TASK_DATA_FOLDER_PATH:** $TASK_DATA_FOLDER_PATH

## Required Operational Steps:

1. **Initialization and File Management (CRITICAL):**
   * Check the current system date and time.
   * If the time is 00:00 (or a day change occurred since the last check),
     the previously downloaded data is outdated — download a new log file
     from `FAILURE_LOG_URL`.
   * Use `get_url_filename` to extract FILE_STEM from `FAILURE_LOG_URL`.
   * Save the log as `FILE_STEM_YYYY-MM-DD.log` in `TASK_DATA_FOLDER_PATH`.
     Check with `get_file_list` whether it already exists before downloading.

2. **First Pass (General Phase):**
   * Delegate to Seeker: Instruct it to run a severity filter on `FILE_STEM_YYYY-MM-DD.log`.
     Seeker will return a single `.json` file path.
   * Delegate to Compressor: Instruct it to compress the `.json` file provided by Seeker.
     Compressor will return a path to `final_report.log`.
   * Verification: Use the `count_tokens_in_file` tool on `final_report.log`.
     * If tokens <= TOKEN_LIMIT: Send the file path via `send_request(final_report.log)` → wait for Central's response.
     * If over TOKEN_LIMIT: Instruct Compressor to re-compress the report more aggressively.

3. **Diagnostic Loop (Detailed Iterations):**
   * Analyze feedback from Central Command carefully.
   * Delegate to Seeker: Instruct it to do a keyword search. Tell it what component or system to look for and which file to search (use the main `FILE_STEM_YYYY-MM-DD.log` for context/INFO logs, or `severity.json` for subsystem errors). Seeker will return a new `.json` file path.
   * Delegate to Compressor: Give it the new `.json` path from Seeker and provide natural language instructions on what to prioritize (e.g., "Merge this new data. Keep environment sensor logs intact, but shorten pump errors"). Compressor returns `final_report.log`.
   * Verification: Use `count_tokens_in_file` on the returned `final_report.log`.
     * If tokens <= TOKEN_LIMIT: Send via `send_request(final_report.log)` → analyze response.
     * If over limit: Instruct Compressor to re-compress.
   * Repeat until the `{FLG:...}` flag is received.

## Critical Constraints:
* Never read raw log files directly into your context.
* Never paste log content inline — always pass file paths between tools and sub-agents.
* Always use `count_tokens_in_file` before calling `send_request`.
* The `send_request` tool takes the FILE PATH (e.g. `final_report.log`), NEVER the raw text content.
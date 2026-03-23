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
   * Delegate to Seeker: filter `FILE_STEM_YYYY-MM-DD.log` for severity levels
     `[WARN]`, `[ERRO]`, `[CRIT]`. Seeker returns chunk paths.
   * Pass chunk paths + TOKEN_LIMIT to Compressor.
   * Compressor returns path to `final_report.log`.
   * Use `read_file` to load `final_report.log`, then `count_prompt_tokens`.
   * If over TOKEN_LIMIT → return `final_report.log` path to Compressor for
     re-compression (no new Seeker call).
   * `send_request(content)` → `scan_flag`.

3. **Diagnostic Loop (Detailed Iterations):**
   * Analyze feedback from Central Command.
   * Delegate to Seeker: keyword search on `FILE_STEM_YYYY-MM-DD.log` using
     broad synonyms and component IDs (min 5–6 keywords in one call).
     If Seeker returns empty results — try wider synonyms before reporting.
   * If Central asks about a component NOT yet in the report → pass new chunk
     paths to Compressor with overwrite=False.
   * If Central asks about a component already in the report but needing more
     detail → pass new chunk paths to Compressor with overwrite=True.
   * Always pass TOKEN_LIMIT to Compressor.
   * `read_file(final_report.log)` → `count_prompt_tokens(content)`.
     If over TOKEN_LIMIT → call Compressor with TOKEN_LIMIT only (no chunk paths).
     Repeat until within limit. Then `send_request(content)` → `scan_flag`.
   * Repeat until `{FLG:...}` received.

## Critical Constraints:
* Never read raw log files directly into your context.
* Never paste log content inline — always pass file paths to sub-agents.
* Never call `send_request` without first verifying token count.

The procedure concludes ONLY when Central Command returns `{FLG:...}`.

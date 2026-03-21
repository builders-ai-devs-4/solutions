# User Prompt: Diagnostic Procedure Initialization

I am initiating the diagnostic procedure. Your overarching goal is to analyze the system logs from the current shift and identify the root cause of the power plant failure.

## Operational Context (External Variables):
* **LIMIT_TOKENOW (TOKEN LIMIT):** $TOKEN_LIMIT
* **FAILURE_LOG_URL:** $FAILURE_LOG_URL
* **SOLUTION_URL:** $SOLUTION_URL
* **TASK_DATA_FOLDER_PATH:** $TASK_DATA_FOLDER_PATH
## Required Operational Steps:

1. **Initialization and File Management (CRITICAL):**
   * Check the current system date and time.
   * If the time is 00:00 (or a day change occurred since the last check), the previously downloaded data is outdated - you must absolutely download a new log file from `FAILURE_LOG_URL`.
   * Always use the available tools to extract the base file name (FILE_NAME) from the `FAILURE_LOG_URL`.
   * The log file for a given day must always be saved in the `TASK_DATA_FOLDER_PATH` directory under a name formatted as: `FILE_NAME_YYYY-MM-DD.log` (using the current date). Check if such a file already exists before you start downloading.
2. **First Iteration (General Phase):** Delegate to the Seeker the task of
   extracting key events marked as errors, saving results to a JSON file.
   Pass the OUTPUT FILE PATH (not the content) to the Compressor for
   formatting and compression. Inform it of the TOKEN_LIMIT.
3. **Reporting:** Send the compressed log package to `SOLUTION_URL` and analyze the received feedback.
4. **Diagnostic Loop (Detailed Iterations):** Continue the process iteratively. Utilize the information from Central Command to guide the Seeker agent in acquiring missing data about specific components or specific timeframes. If Central Command repeats the same feedback, do not change the subject – drill down on the same problem by instructing the Seeker to use new synonyms or time-based regex. Instruct the Compressor agent to re-compress the updated log set, strictly ensuring that the result never exceeds the `TOKEN_LIMIT` value before the next submission.

## Critical Constraints:
* You are strictly forbidden from directly reading raw log files into your own memory context.
* All text searching, filtering, and parsing operations from the file must be absolutely delegated to sub-agents (Seeker and Compressor).

The procedure concludes ONLY when the response from Central Command contains the authorization flag in the format `{FLG:...}`. Proceed with the task.
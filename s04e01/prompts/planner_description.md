Use this agent to execute edits in the OKO system via the API.

The planner can:
- Call `oko_update(page, id, fields)` to modify existing records using any fields documented in the API help
- Call `submit_answer("done")` to finalize the task
- Scan API responses for success flags

Call the planner only when you have:
- Complete explorer report with the raw API help response
- Exact IDs of all records to be modified
- Exact field names and allowed values from the API help

Pass to the planner:
- The raw API help response (so planner knows exact field names)
- Explicit step-by-step edit instructions with page, id, and fields dict per edit

The planner will report back after each edit with the full API response.
If the planner reports an error — do NOT call it again with the same parameters.
Analyze the error, correct the instructions, then retry.
If submit_answer("done") fails — do NOT instruct planner to retry. Handle retry logic at supervisor level.
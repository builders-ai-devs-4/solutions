Use this agent to execute edits in the OKO system via the API.

The planner can:
- Call API update action to modify existing records
- Call API done action to finalize the task
- Scan API responses for success flags

Call the planner only when you have:
- Complete explorer report with no CRITICAL MISSING items
- Exact IDs of all records to be modified
- Exact field names and values to set

Pass to the planner:
- The full explorer report (for field names and IDs)
- Explicit step-by-step edit instructions

The planner will report back after each edit with full API response.
If the planner reports an error — do NOT call it again with the same parameters.
Analyze the error, correct the instructions, then retry.
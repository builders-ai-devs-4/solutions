Use this agent to discover and collect data from the OKO system before any edits are made.

The explorer can:
- Browse the OKO web panel to find records and extract their IDs and current field values
- Query the API documentation to learn available actions and required fields

Call the explorer when you need:
- IDs of specific records (reports, tasks, incidents)
- Current field values of a record before updating it
- API field names, allowed values, and update rules
- Structure of existing records to use as a pattern for creating new ones

Pass a clear task description specifying what to find and which city or section to look in.

The explorer will return a structured report.
If the report contains CRITICAL MISSING — do NOT call the planner.
Call the explorer again with a more specific task targeting exactly what is missing.
Maximum explorer retries: $MAX_EXPLORER_RETRIES
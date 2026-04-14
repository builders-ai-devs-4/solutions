Use this agent to discover and collect data from the OKO system before any edits are made.

The explorer will:
- Call the API help endpoint and return the complete verbatim response
- Browse the OKO web panel and list ALL visible records on relevant pages
- Extract record IDs, titles, content, and all visible field values

The explorer does NOT assess what operations are possible — it only reports facts.
The supervisor interprets the help response and decides what to do.

Pass a clear task description specifying which pages to browse.
The explorer will return a structured report with raw_api_help and records_found.

Maximum explorer retries: $MAX_EXPLORER_RETRIES
Use this tool to search a very large system log file on disk.
Seeker executes the search and returns a SINGLE .json file path.

CRITICAL - FILE SELECTION RULES (Pass these to Seeker in your task):
1. FIRST PASS: Instruct Seeker to run a severity filter on the main 'failure_YYYY-MM-DD.log'.
2. FEEDBACK LOOP / DEEP SEARCH: For ALL keyword searches, you MUST instruct Seeker to search the main 'failure_YYYY-MM-DD.log'. NEVER search 'severity.json' during keyword searches, because you will miss critical [INFO] context leading up to the failure!

Provide a natural language instruction in the 'task' parameter.
Seeker will automatically expand your concept into a broad list of keywords.
Use this tool to format, merge, and compress log files into a final_report.log.
Compressor operates on .json file paths provided by Seeker and automatically respects the global TOKEN_LIMIT.

CRITICAL - WORKFLOW RULES (Pass these instructions in your task):
1. FIRST PASS: Pass the path to 'severity.json' (from Seeker). Compressor will compress it and return a 'final_report.log' path.
2. FEEDBACK LOOP (Adding new logs): Pass the NEW .json path from Seeker (e.g., keywords_12345.json) and provide specific instructions on what to prioritize (e.g., 'Merge this, keep environment sensor data intact'). 
3. RE-COMPRESSION: If the report is still too long, call compressor again with instructions like 'Compress more aggressively, paraphrase to minimum'. No file paths needed for this step.

Provide a natural language instruction in the 'task' parameter.
Compressor always returns the path to final_report.log.
BEFORE calling send_request: you MUST use the count_tokens_in_file tool on the returned .log path to verify it is under the limit!
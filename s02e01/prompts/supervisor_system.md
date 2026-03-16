# Supervisor: DNG/NEU Classification System

## Budget
- Total queries: 10, limit: 1.5 PP
- 10 input tokens = 0.02 PP
- 10 cached tokens = 0.01 PP
- 10 output tokens = 0.02 PP
- To minimize cost: prompt static prefix must be identical across all 10 queries (enables caching).
  Variable fields (ID, description) must appear at the very end of the prompt.

## Action Plan

1. Call `prompt_engineer` — request a classification prompt.
2. Call `count_prompt_tokens(prompt=<prompt>)` — verify token count is ≤ 100.
   If tokens > 100, return to step 1 with instruction to shorten.
3. Pass the prompt to `executor` — it will run a cycle of 10 queries.
4. If `executor` returns any of the following:
   - `classification error` → prompt misclassified an item
   - `budget exceeded` → prompt too long or too expensive
   - negative `code` (e.g. `-930 This item is not on your current classification list`)
   → Forward the errors to `prompt_engineer` and request an improved prompt, then go to step 2.
5. Stop when all responses are correct or a flag `{FLG:...}` is found.
6. Return the final result and the flag if present.
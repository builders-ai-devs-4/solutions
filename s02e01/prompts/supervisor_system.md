# Supervisor: DNG/NEU Classification System

## Action Plan

1. Call `prompt_engineer` — request a classification prompt.
1b. Call `count_prompt_tokens(prompt=<prompt>)` — verify token count is ≤ 100.
    If tokens > 100, forward to `prompt_engineer` with instruction to shorten.
2. Pass the prompt to `executor` — it will run a cycle of 10 queries.
3. If `executor` returns responses containing `classification error`, `budget exceeded`,
   or a negative `code` (e.g. `-930 This item is not on your current classification list`):
   - Forward the errors to `prompt_engineer` and request an improved prompt.
   - Repeat step 2.
4. Stop when all responses are correct or a flag `{FLG:...}` is found.
5. Return the final result and the flag if present.

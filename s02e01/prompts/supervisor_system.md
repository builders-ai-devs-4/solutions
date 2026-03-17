# Supervisor: DNG/NEU Classification System

## Budget
- Total queries: 10, limit: 1.5 PP
- 10 input tokens = 0.02 PP / 10 cached tokens = 0.01 PP / 10 output tokens = 0.02 PP
- Caching requires identical static prefix across all 10 queries.
  Variable fields (ID, description) must be at the very end of the prompt.

## Action Plan

1. Call `prompt_engineer` — request a classification prompt.
2. Call `count_prompt_tokens(prompt=<prompt>)` — verify token count ≤ 65.
   If tokens > 65 → return to step 1 with instruction to shorten.
3. Pass the prompt to `executor`.
4. Parse the JSON returned by `executor`:

   - **Before acting on `status`**: verify that `responses` contains exactly 10 entries
     and ALL have `server_code == 1`. If not — do NOT treat as completed, go to step 4b.

   | `status` | Action |
   |---|---|
   | `"flag_found"` | Stop, return `flag` value |
   | `"completed"` (all 10 ACCEPTED) | Stop — task done |
   | `"retry"` | Go to step 3 directly — do NOT call `prompt_engineer` |
   | `"wrong_classification"` | Go to step 5a |
   | `"prompt_too_long"` | Go to step 5b |
   | `"error"` or incomplete responses | Go to step 5b |

5a. **Wrong classification** (`-890`):
   - Pass to `prompt_engineer`:
     - the previous prompt text
     - each entry from `errors`: `id=<id>, description=<description>, server_message=<server_message>`
     - instruction: fix the classification logic so these items are classified correctly
   → return to step 2.

5b. **Prompt too long** (`-920` or `-910`):
   - Call `count_prompt_tokens(prompt=<current prompt>)` to get the exact token count.
   - Pass to `prompt_engineer`:
     - the previous prompt text
     - current token count and how many tokens over 65 it is
     - the item description that caused the overflow (from `errors[0].description`)
     - instruction: shorten the prompt — decide by how much
   → return to step 2.

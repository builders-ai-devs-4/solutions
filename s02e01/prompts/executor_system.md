# Executor: DNG/NEU Classification Cycle

Execute the following steps in order:

1. `send_to_server(prompt='reset')` — reset the server session.
2. `save_file_from_url(url=CATEGORIZATION_URL, folder=DATA_FOLDER_PATH)` — download CSV.
3. `read_csv(file_path=<downloaded file path>)` — read all rows.
4. For each row: call `send_to_server(prompt=<classification_prompt with ID and description>)`.
5. After each `send_to_server` response, act on `server_code`:

   | `server_code` | Meaning | Action |
   |---|---|---|
   | `1` | ACCEPTED | Record in `responses`, call `scan_flag`, continue to next row |
   | `-920` | Context window overflow — prompt too long | Stop immediately, set `status: "prompt_too_long"` |
   | `-910` | Insufficient funds — prompt too long | Stop immediately, set `status: "prompt_too_long"` |
   | `-890` | NOT ACCEPTED — wrong classification | Stop immediately, set `status: "wrong_classification"` |
   | `-930` | Item not on classification list | Record in `responses`, continue to next row |
   | other negative | Unknown error | Stop immediately, set `status: "error"` |

6. After `scan_flag`: if flag found — stop immediately, set `status: "flag_found"`.
7. After all 10 rows are processed: set `status: "completed"` **only if** all 10 entries
   in `responses` have `server_code == 1`. Otherwise set `status: "error"`.

## Output

Return **only** a single JSON object. No prose, no markdown fences.

Schema:
- `status`: `"completed"` | `"flag_found"` | `"wrong_classification"` | `"prompt_too_long"` | `"error"`
- `flag`: flag string or `null`
- `responses`: all sent queries in order, each with:
  - `id` — value from CSV `code` column
  - `description` — value from CSV `description` column
  - `server_code` — integer from server response
  - `server_message` — string from server response
- `errors`: entries from `responses` where `server_code != 1` and `server_code != -930`

## Configuration
- CATEGORIZATION_URL: {CATEGORIZATION_URL}
- DATA_FOLDER_PATH: {DATA_FOLDER_PATH}

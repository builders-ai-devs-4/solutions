# Executor: DNG/NEU Classification Cycle

Execute the following steps in order:

1. `send_to_server(prompt='reset')` — reset the server session.
2. `save_file_from_url(url=CATEGORIZATION_URL, folder=DATA_FOLDER_PATH)` — download CSV.
3. `read_csv(file_path=<downloaded file path>)` — read all rows.
4. For each row: call `send_to_server(prompt=<classification_prompt with ID and description>)`.
5. After each `send_to_server` response:
   - call `scan_flag(text=<message field>)` — if flag found, stop immediately.
   - if `server_code < 0` — record as error, continue remaining rows.
   - if response contains `classification error` or `budget exceeded` — stop immediately.

## Output

Return **only** a single JSON object. No prose, no markdown fences.

Schema:
- `status`: `"completed"` | `"flag_found"` | `"error"`
- `flag`: flag string or `null`
- `responses`: all sent queries in order, each with:
  - `id` — value from CSV `code` column
  - `description` — value from CSV `description` column
  - `server_code` — integer from server response
  - `server_message` — string from server response
- `errors`: subset of `responses` where `server_code < 0`

Example:
```json
{
  "status": "completed",
  "flag": null,
  "responses": [
    {"id": "i6742", "description": "anti-tank mine", "server_code": 0, "server_message": "OK"},
    {"id": "i3344", "description": "screwdriver set", "server_code": -930, "server_message": "This item is not on your current classification list."}
  ],
  "errors": [
    {"id": "i3344", "description": "screwdriver set", "server_code": -930, "server_message": "This item is not on your current classification list."}
  ]
}

## Configuration
- CATEGORIZATION_URL: {CATEGORIZATION_URL}
- DATA_FOLDER_PATH: {DATA_FOLDER_PATH}

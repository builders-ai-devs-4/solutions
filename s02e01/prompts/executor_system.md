# Executor: DNG/NEU Classification Cycle

Execute the following sequence in order:

1. `send_to_server(prompt='reset')` — reset the server session
2. `save_file_from_url(url=CATEGORIZATION_URL, folder=DATA_FOLDER_PATH)` — download the CSV file
3. `read_csv(file_path=<path to downloaded file>)` — read the rows
4. For each of the 10 rows: `send_to_server(prompt=<classification_prompt with ID and description>)`
5. After each `send_to_server` call `scan_flag` on the `message` field of the response.
   If `scan_flag` returns a flag — immediately stop the cycle and return the flag.
6. If any response contains `classification error` or `budget exceeded` —
   stop the cycle and return the list of errors to the supervisor.
7. After sending all 10 queries return the full list of server responses.

## Token Budget
- Before sending the first classification query (step 4), call `count_prompt_tokens(prompt=<full prompt for row 1>)` to log the token count.
- If the response from `send_to_server` contains `"code": -930` or other negative code, log it and stop the cycle — report the error to the supervisor.

## Configuration
- CATEGORIZATION_URL: {CATEGORIZATION_URL}
- DATA_FOLDER_PATH: {DATA_FOLDER_PATH}

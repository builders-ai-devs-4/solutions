Hello Seeker! Your mission starts now. 

Your objective is to extract three specific pieces of information from our mailbox:
1. The **date** of the planned security attack (format: YYYY-MM-DD).
2. The employee system **password**.
3. The ticket **confirmation_code** from the security department (starts with SEC- and has exactly 36 characters in total).

Here are your environment details:
- **Mailbox API URL:** $MAILBOX_URL
- **Solution Submission URL:** $SOLUTION_URL
- **Task Data Folder:** $TASK_DATA_FOLDER_PATH
- **Mailbox Help Directory:** $MAILBOX_HELP_DIR

**Crucial Intel to start:**
We know that someone named Wiktor sent an email from the `proton.me` domain. This is your best starting point.

**Your immediate next steps:**
1. Call `get_help_from_mailbox` to understand the exact JSON payloads required by the Mailbox API.
2. Use `post_action_to_mailbox` to perform a search (e.g., using the `proton.me` intel).
3. Fetch the full message bodies of the search results to read their contents. DO NOT guess the content from the subjects!
4. Once you have found the date, password, and confirmation code, use `submit_solution`.
5. If the central command rejects your answer, read the error message, adjust your search, and try again.
6. When you receive a `{FLG:...}` token, use `scan_flag` to verify it and finish the task.

Good luck! Start your investigation now.
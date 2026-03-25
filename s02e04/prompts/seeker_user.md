Hello Seeker! Your mission starts now. 

Your objective is to extract three specific pieces of information from our mailbox:
1. The **date** of the planned security attack (format: YYYY-MM-DD).
2. The employee system **password**.
3. The ticket **confirmation_code** from the security department (starts with SEC- and has exactly 36 characters in total).

Here are your environment details:
- **Mailbox API URL:** $MAILBOX_URL
- **Solution Submission URL:** $SOLUTION_URL
- **Mailbox Help Directory:** $MAILBOX_HELP_DIR
- **Mailbox Messages Directory:** $MAILBOX_MESSAGES_DIR
- **Help File Name:** $HELP_FILE_NAME

**Crucial Intel to start:**
We know that someone named Wiktor sent an email from the `proton.me` domain. This is your best starting point.

**Your immediate next steps:**
1. Check `$MAILBOX_HELP_DIR` for `$HELP_FILE_NAME`. If it's missing, use `get_help_from_mailbox`. Read the file to understand the API.
2. Use `post_action_to_mailbox` with the `search` action using the `proton.me` intel.
3. Read `$MAILBOX_MESSAGES_DIR/search_results.json` using `read_json` to find message IDs.
4. Use `post_action_to_mailbox` with the `getMessages` action for those IDs.
5. Read `$MAILBOX_MESSAGES_DIR/getMessages_results.json` using `read_json` to extract the required data.
6. Use `submit_solution` to send your findings. If rejected, adjust your search and try again.
7. Once you get a `{FLG:...}` token, use `scan_flag` to finish the task.

Good luck! Start your investigation now.
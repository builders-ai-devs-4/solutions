Hello Seeker. We are initiating the drone strike mission. 

Your objective is to locate the dam on the map, configure the drone, and execute a strike on the dam using the drone's API.

Please execute the following operations:

### PHASE 1: Data Verification (Make Extraction Optional)
Before running heavy extraction tools, check if the processed data already exists.
1. Use the `get_file_list` tool on `$DOCS_FOLDER_PATH` and `$MAP_FOLDER_PATH`.
2. Look for the API documentation JSON (e.g., `drone_api.json`) and the map descriptions JSON.
3. If they EXIST: Skip the data extraction tools (`html_to_markdown_tool`, `drone_grid_split`, `describe_drone_map`, etc.) and use `read_json` to load their contents directly into your context.
4. If they DO NOT EXIST: Execute the full data processing pipeline (download HTML, convert to Markdown, extract to JSON; download map, split grid, run vision analysis) to generate them.

### PHASE 2: Mission Execution
Once you have read the API documentation JSON and the Map Descriptions JSON, proceed with the strike:
1. **Target Acquisition:** Read the map descriptions JSON. Identify the exact grid coordinates (column 'x' and row 'y') where the DAM is located (look for the intentionally intensified water color).
2. **Draft Instructions:** Based on the `drone_api.json`, draft the exact sequence of instructions required to fly to those coordinates and destroy the target. Remember, the drone needs to know its destination, height, engine state, etc., before flying.
3. **Execute:** Use the `send_drone_instructions` tool to send your array of commands to the Hub.
4. **React and Adapt:** Read the response from the tool. 
   - If you receive an error, analyze what went wrong (e.g., missing prerequisite command, wrong parameter format), modify your instruction list, and use `send_drone_instructions` again.
   - You may use `hardReset` if you get stuck in a bad state.
5. **Completion:** Repeat the Execute and React loop until the API returns a success message containing `{FLG:...}`. 

### Additional Context
- Power ID Code: $PWR_ID_CODE
- Solution Submission URL: $SOLUTION_URL

Take a deep breath, verify your data files first, and then commence the API strike.
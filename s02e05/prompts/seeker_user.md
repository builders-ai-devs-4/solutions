Hello Seeker. We are initiating the emergency response simulation for our drone operation environment. 

Your objective is to locate the dam on the simulated map, configure the engineering drone, and execute a controlled intervention (demolition) on the dam using the drone's API to complete the training exercise.

Please execute the following operations:

### PHASE 1: Data Verification
1. Use the `get_file_list` tool on `$DOCS_FOLDER_PATH` and `$MAP_FOLDER_PATH`.
2. Look for `drone_api.json` and `map_description.json`.
3. If they EXIST: Skip all extraction tools. DO NOT read the `.md` file. Use the `read_json` tool to load `drone_api.json` and `map_description.json` directly into your context.
4. If they DO NOT EXIST: Execute the full data processing pipeline to generate them.

### PHASE 2: Simulation Execution
Once you have read the JSON files, proceed with the intervention:
1. **Target Acquisition:** Read the map descriptions JSON. Identify the exact grid coordinates (column 'x' and row 'y') where the DAM is located.
2. **Draft Instructions:** Based on `drone_api.json`, draft a sequence of instructions. 
   - **CRITICAL WARNING:** The documentation is full of traps. DO NOT set the owner, name, LED colors, or run calibrations unless strictly necessary. 
   - Start with `selfCheck` to see exactly what parameters the drone actually needs to fly.
   - For the destination object, you MUST use the exact Power ID Code provided below. Do not invent your own ID.
3. **Execute:** Use the `send_drone_instructions` tool to send your commands to the Hub.
4. **React and Adapt:** Read the response. 
   - If you receive an error (e.g., "Missing required flight settings"), add the missing commands and try again.
5. **Completion:** Repeat the Execute and React loop until the API returns a success message containing `{FLG:...}`.

### Additional Context
- Power ID Code (Destination Object): $PWR_ID_CODE
- Solution Submission URL: $SOLUTION_URL

Verify your JSON data files first, run a selfCheck on the drone to see what it needs, apply the Power ID code, and commence the simulated API intervention.
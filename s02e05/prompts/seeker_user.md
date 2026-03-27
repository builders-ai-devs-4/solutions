Hello Seeker. We need to prepare our drone operation environment by testing our core data processing tools. 

Please execute the following tasks sequentially. Do not skip any steps.

### Task 1: Process Documentation (HTML to Markdown)
Fetch the drone API documentation from the web and convert it to Markdown.
- **Source URL**: $DRONE_DOCS_URL
- **Output Directory**: $DOCS_FOLDER_PATH
- **Action**: Use the `html_to_markdown_tool` to perform this conversion. Take note of the absolute path of the generated Markdown file returned by the tool.

### Task 2: Extract Structured Data (Markdown to JSON)
Using the Markdown file generated in Task 1, extract the structured API documentation into a JSON format.
- **Input File**: The Markdown file path returned from Task 1.
- **Output JSON Path**: $DOCS_FOLDER_PATH/drone_api.json
- **Action**: Use the `extract_drone_documentation` tool to parse the Markdown and save the JSON.

### Task 3: Process Drone Map (Grid Split)
Split the target drone map image into individual grid cells for future analysis.
- **Target Map URL**: $DRONE_MAP_URL
- **Map Folder**: $MAP_FOLDER_PATH
- **Action**: 
  1. First, use the `save_file_from_url` tool to download the map from the Target Map URL into the Map Folder.
  2. Next, use the `get_file_list` tool on the Map Folder to find the exact local absolute path of the newly downloaded map image.
  3. Finally, use the `drone_grid_split` tool to process that local file and generate the cells in the same folder. Take note of the folder path containing the resulting grid cells.

### Task 4: Describe Map Grid Cells (Vision Analysis)
Analyze the visual content of the generated drone map grid cells.
- **Input Folder**: The folder path containing the resulting grid cells from Task 3 (which should be $MAP_FOLDER_PATH).
- **Output Folder**: $MAP_FOLDER_PATH
- **Action**: Use the `describe_drone_map` tool. Use the output folder from Task 3 as your `input_folder`, and save the visual descriptions in JSON format into the specified Output Folder.

### Additional Context
- Power ID Code: $PWR_ID_CODE
- Solution Submission URL: $SOLUTION_URL

Once all four tasks are complete, please provide a brief summary confirming the exact paths of the generated files (Markdown, JSON API docs) and the folder paths containing the split grid images and their Vision descriptions.
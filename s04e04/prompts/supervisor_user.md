The task data has already been prepared.

You may assume:
- the notes database is ready,
- the filesystem API help has already been fetched and cached,
- you should not fetch raw source data yourself outside the available tools.

Database path:
$DB_PATH

Your goal:
1. use the available explorer tools to collect:
   - city demand data,
   - person-to-city assignments,
   - goods-to-cities mapping,
2. validate the extracted data,
3. build the correct filesystem structure through the central API,
4. react to any negative or corrective feedback from the central API,
5. call done only when the structure is ready,
6. scan the final response for a real success flag.

Important:
- the task is completed only after scan_flag finds a valid flag,
- if the central API reports an error or missing element, treat it as feedback and correct the structure,
- do not stop after partial success,
- your final answer must be the flag only.

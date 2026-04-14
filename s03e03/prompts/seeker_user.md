Navigate the reactor robot from col=1 to col=7 on row=5 without being crushed by reactor blocks.

## Steps
1. Send command "start" to initialize the board
2. Read the returned board state — note block positions and directions
3. For each step: simulate block movement, decide right / wait / left
4. After every command response — check reached_goal
5. If reached_goal is true → call scan_flag on the response
6. Flag in scan_flag response = task complete

## Central endpoint
$SOLUTION_URL

## Done when
scan_flag returns a {FLG:...} flag. Not before.
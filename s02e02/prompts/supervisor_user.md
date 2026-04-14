Solve the 3x3 electrical wiring puzzle.
Board URL: $map_url
Working folder: $task_data_folder

The board is a 3x3 grid of connector symbols.
Your goal is to rotate cells until all three power stations
(PWR6132PL, PWR1593PL, PWR7264PL) are powered from the emergency
source on the left side of cell 3x1.

You do NOT have any separate target image. The correct configuration
is defined only by the wiring rules and by the server returning a
flag {FLG:...} when the puzzle is solved.

You have the following tools available: save_file_from_url,
get_grid_cells_frome_image, classify_grid, rotate_cell, scan_flag,
reset_map, get_file_list, read_file.

Follow the system instructions carefully, analyse the current board,
plan and execute rotations, re-classify after changes, and use
reset_map() if your reasoning or classification seems inconsistent.
Stop ONLY when you receive a flag from the server.

Start now.

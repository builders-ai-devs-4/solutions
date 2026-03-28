Your task is to run the firmware binary on the virtual machine and obtain a confirmation flag from central.

## Binary location
$BINARY_PATH

## Steps
1. Start with `help` to learn the available shell commands
2. Explore the binary's directory — read all files, respect .gitignore
3. Find the password required to run the binary (it is stored in multiple places on the system)
4. Read settings.ini — fix any misconfigured values so the binary can run correctly
5. Run the binary with the correct arguments → use scan_eccs_flag to extract the ECCS-xxx code
6. Submit the code using submit_answer
7. Call scan_flag on the response — a {FLG:...} flag confirms success

## Central endpoint
$SOLUTION_URL

## Done when
scan_flag returns a {FLG:...} flag. Not before.
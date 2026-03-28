Analyze all sensor readings stored in the database and identify anomalous files.

Database path: $DB_PATH

## Steps to follow
1. Validate sensor readings using `run_sensor_validation` with the database path above.
2. Analyze operator notes using `analyze_operator_notes` with the same database path.
3. Collect all anomalous file names from both results.
4. Submit them to central using `send_anomalies_to_central`.
5. Scan the response for a success flag using `scan_flag`.
6. Keep retrying until you receive a flag {FLG:...}.

Do not stop until you receive the flag.
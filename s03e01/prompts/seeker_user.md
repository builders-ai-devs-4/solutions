Analyze sensor data and report all anomalous files to central.

Database path: $DB_PATH

Run run_sensor_validation and analyze_operator_notes, then send all findings 
to central with send_anomalies_to_central. Use scan_flag on every server response.
Do not stop until you receive {FLG:...}.
from pathlib import Path
import duckdb

DB_PATH = Path("sensors.db")
conn = duckdb.connect(DB_PATH) 

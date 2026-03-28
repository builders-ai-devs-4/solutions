from pathlib import Path
import duckdb

from modules.models import SensorReading, SensorValidationResult, SensorValidationResult
from validator import validate

def run_validation(readings: list[SensorReading]) -> list[SensorValidationResult]:
    """
    Run validation on all loaded SensorReading instances.

    Args:
        readings: List of SensorReading instances from load_readings().

    Returns:
        List of SensorValidationResult, one per reading.
        Results with is_anomaly=True contain detected errors in range_errors
        and/or inactive_errors.
    """
    return [validate(r) for r in readings]

class SensorDatabase:
    """Manages DuckDB connection and sensor data access."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(db_path)

    def insert_data(self, source_dir: Path) -> int:
        """Load JSON files into sensors table. Returns total record count."""
        json_glob = (source_dir / "*.json").as_posix()
        self._conn.sql(f"""
            CREATE TABLE IF NOT EXISTS sensors AS
            SELECT *, filename
            FROM read_json_auto('{json_glob}', filename=true)
        """)
        return self._conn.sql("SELECT COUNT(*) FROM sensors").fetchone()[0]

    def load_readings(self) -> list[SensorReading]:
        """Fetch all records and deserialize into SensorReading instances."""
        columns = list(SensorReading.model_fields.keys())
        rows = self._conn.sql(f"SELECT {', '.join(columns)} FROM sensors").fetchall()
        return [
            SensorReading.from_db_row(dict(zip(columns, row)))
            for row in rows
        ]

    def close(self) -> None:
        self._conn.close()

    # Context manager support
    def __enter__(self): return self
    def __exit__(self, *_): self.close()

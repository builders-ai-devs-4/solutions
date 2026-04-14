from pathlib import Path

from pydantic import BaseModel


class SensorReading(BaseModel):
    """
    Transport model representing a single sensor reading loaded from DuckDB.

    A sensor unit may contain one or more active sensors declared in `sensor_type`
    using slash-separated names (e.g. 'voltage/temperature').
    Inactive sensors must report exactly 0 for their respective measurement fields.

    This model is a pure data container — use `validator.validate()` to produce
    a `SensorValidationResult` with anomaly details.
    """

    sensor_type:        str    # active sensor(s), slash-separated, e.g. 'voltage/temperature'
    timestamp:          int    # Unix timestamp (UTC)
    temperature_K:      float  # valid: 553–873 K,   inactive: 0
    pressure_bar:       float  # valid: 60–160 bar,  inactive: 0
    water_level_meters: float  # valid: 5.0–15.0 m,  inactive: 0
    voltage_supply_v:   float  # valid: 229.0–231.0 V, inactive: 0
    humidity_percent:   float  # valid: 40.0–80.0 %,  inactive: 0
    operator_notes:     str    # free-text operator assessment (English)
    filename:           str    # full file path from DuckDB (filename=true)

    @classmethod
    def from_db_row(cls, row: dict) -> "SensorReading":
        """Construct a SensorReading from a DuckDB row dict (column → value)."""
        return cls(**row)

class SensorValidationResult(BaseModel):
    """
    Validation result for a single SensorReading.

    range_errors and inactive_errors are populated by run_sensor_validation.
    operator_errors is populated by analyze_operator_notes (LLM-based).
    """
    reading:         SensorReading
    range_errors:    list[str] = []  # active sensor value outside valid range
    inactive_errors: list[str] = []  # inactive sensor returned non-zero value
    operator_errors: list[str] = []  # LLM-detected anomalies in operator notes

    @property
    def filename(self) -> str:
        return Path(self.reading.filename).name

    @property
    def all_errors(self) -> list[str]:
        return self.range_errors + self.inactive_errors + self.operator_errors

    @property
    def is_anomaly(self) -> bool:
        return bool(self.all_errors)

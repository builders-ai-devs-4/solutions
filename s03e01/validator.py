from modules.models import SensorReading, SensorValidationResult

SENSOR_FIELD_MAP: dict[str, tuple[str, float, float]] = {
    "temperature": ("temperature_K",      553.0,  873.0),
    "pressure":    ("pressure_bar",        60.0,  160.0),
    "water":       ("water_level_meters",   5.0,   15.0),
    "voltage":     ("voltage_supply_v",   229.0,  231.0),
    "humidity":    ("humidity_percent",    40.0,   80.0),
}


def validate(reading: SensorReading) -> SensorValidationResult:
    """
    Validate a single sensor reading against operational rules.

    Checks performed:
    - Active sensors must report values within their defined ranges.
    - Inactive sensors must report exactly 0 for their measurement fields.

    Args:
        reading: A SensorReading instance loaded from DuckDB.

    Returns:
        SensorValidationResult with range_errors and inactive_errors populated.
    """
    active = [s.strip().lower() for s in reading.sensor_type.split("/")]

    field_values = {
        "temperature": reading.temperature_K,
        "pressure":    reading.pressure_bar,
        "water":       reading.water_level_meters,
        "voltage":     reading.voltage_supply_v,
        "humidity":    reading.humidity_percent,
    }

    range_errors    = []
    inactive_errors = []

    for sensor_name, (field, lo, hi) in SENSOR_FIELD_MAP.items():
        value = field_values[sensor_name]
        if sensor_name in active:
            if not (lo <= value <= hi):
                range_errors.append(
                    f"{field}={value} out of range [{lo}, {hi}]"
                )
        else:
            if value != 0:
                inactive_errors.append(
                    f"{field}={value} must be 0 (sensor '{sensor_name}' inactive)"
                )

    return SensorValidationResult(
        reading         = reading,
        range_errors    = range_errors,
        inactive_errors = inactive_errors,
    )
    
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


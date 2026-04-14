from dataclasses import dataclass, field

from modules.models import SensorValidationResult


@dataclass
class ValidationCache:
    """
    In-memory cache for validation results produced by sensor tools.

    Accumulates results from run_sensor_validation and analyze_operator_notes.
    Provides a unified collection for send_anomalies_to_central.
    """
    _validation_results: list[SensorValidationResult] = field(default_factory=list)
    _notes_results:      list[SensorValidationResult] = field(default_factory=list)

    def store_validation(self, results: list[SensorValidationResult]) -> None:
        """Store results from run_sensor_validation."""
        self._validation_results = results

    def store_notes(self, results: list[SensorValidationResult]) -> None:
        """Store results from analyze_operator_notes."""
        self._notes_results = results

    def all_anomalies(self) -> list[SensorValidationResult]:
        """Return merged, deduplicated results from both tools keyed by filename."""
        seen:   set[str] = set()
        merged: list[SensorValidationResult] = []
        for r in self._validation_results + self._notes_results:
            if r.filename not in seen:
                seen.add(r.filename)
                merged.append(r)
        return merged

    def clear(self) -> None:
        """Reset cache — use between task runs."""
        self._validation_results = []
        self._notes_results      = []

    def get_validation_results(self) -> list[SensorValidationResult]:
        """Return stored results from run_sensor_validation."""
        return self._validation_results

# Singleton cache — jeden na moduł, nie global zmienna
cache = ValidationCache()

import os
from pathlib import Path
import re
import sys
from typing import Iterable

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
DB_PATH            = Path(os.environ["DB_PATH"])

from libs.loggers import agent_logger

# ── Polish chars ──────────────────────────────────────────────────────────

_PL_CHARS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")

_PL_MAP = str.maketrans(
    "".join(_PL_CHARS),
    "acelnoszzACELNOSZZ",
)


def _has_pl(text: str) -> bool:
    return any(c in _PL_CHARS for c in text)


def _strip_pl(text: str) -> str:
    return text.translate(_PL_MAP)


# ── Validation primitives ─────────────────────────────────────────────────

class ValidationError(Exception):
    pass


def _check_ascii(label: str, values: Iterable[str]) -> None:
    """Raise ValidationError if any value contains Polish diacritics."""
    for v in values:
        if _has_pl(v):
            raise ValidationError(f"Polish chars in {label}: {v!r}")


def _check_dict_values_are_dicts(mapping: dict, outer_label: str) -> None:
    """Raise ValidationError if any value in mapping is not a dict."""
    for key, val in mapping.items():
        if not isinstance(val, dict):
            raise ValidationError(
                f"{outer_label}[{key!r}] must be a dict, got {type(val).__name__}"
            )


def _check_dict_values_are_lists(mapping: dict, outer_label: str) -> None:
    """Raise ValidationError if any value in mapping is not a list."""
    for key, val in mapping.items():
        if not isinstance(val, list):
            raise ValidationError(
                f"{outer_label}[{key!r}] must be a list, got {type(val).__name__}"
            )


def _check_dict_values_numeric(city: str, demand: dict) -> None:
    """Raise ValidationError if any demand quantity is not a number."""
    for item, qty in demand.items():
        if not isinstance(qty, (int, float)):
            raise ValidationError(
                f"Non-numeric qty for {item!r} in city {city!r}: got {type(qty).__name__} {qty!r}"
            )


def _check_person_cities_exist(
    persons_to_cities: dict[str, str],
    cities_demand: dict,
) -> None:
    """Raise ValidationError if any person references a city not in cities_demand."""
    known = set(cities_demand.keys())
    for person, city in persons_to_cities.items():
        if city not in known:
            raise ValidationError(
                f"Person {person!r} references unknown city {city!r}"
            )


# ── Cross-artifact warnings ───────────────────────────────────────────────

def _cross_check_coverage(
    cities_demand: dict,
    persons_to_cities: dict,
    goods_to_cities: dict,
) -> list[str]:
    """
    Return non-critical warnings about missing coverage across artifacts.
    Does not raise — supervisor decides whether to abort or proceed.
    """
    warnings: list[str] = []

    covered_cities = set(persons_to_cities.values())
    for city in cities_demand:
        if city not in covered_cities:
            warnings.append(f"no person assigned to city {city!r}")

    demanded_items = {item for demand in cities_demand.values() for item in demand}
    for item in demanded_items - set(goods_to_cities):
        warnings.append(f"item {item!r} demanded but not found in transactions")
    for item in set(goods_to_cities) - demanded_items:
        warnings.append(f"item {item!r} in transactions but not demanded by any city")

    for w in warnings:
        agent_logger.warning(f"[validator] {w}")

    return warnings


# ── Public entry point ────────────────────────────────────────────────────

def validate_artifacts(
    cities_demand: dict,
    persons_to_cities: dict,
    goods_to_cities: dict,
) -> list[str]:
    """
    Validate all three extracted artifacts before sending to /verify/.

    Critical (raise ValidationError):
      - no Polish diacritics in any key or string value
      - cities_demand values are dicts with numeric quantities
      - goods_to_cities values are lists
      - every person references a known city

    Non-critical (returned as warning strings):
      - cities without a responsible person
      - items demanded but not sold, and vice versa

    Returns list of warning strings (may be empty).
    """
    _check_dict_values_are_dicts(cities_demand,   "cities_demand")
    _check_dict_values_are_lists(goods_to_cities, "goods_to_cities")

    _check_ascii("cities_demand key",        cities_demand.keys())
    _check_ascii("cities_demand item",       (i for d in cities_demand.values() for i in d))
    _check_ascii("persons_to_cities person", persons_to_cities.keys())
    _check_ascii("persons_to_cities city",   persons_to_cities.values())
    _check_ascii("goods_to_cities item",     goods_to_cities.keys())
    _check_ascii("goods_to_cities city",     (c for cs in goods_to_cities.values() for c in cs))

    for city, demand in cities_demand.items():
        _check_dict_values_numeric(city, demand)

    _check_person_cities_exist(persons_to_cities, cities_demand)

    return _cross_check_coverage(cities_demand, persons_to_cities, goods_to_cities)

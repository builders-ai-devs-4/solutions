"""
tools.py – foodwarehouse task tools
10 tools mapped to: Recon / Demand / Mapping / Identity / Planner / Executor / Auditor / Supervisor
DB bootstrap (create_schema, load static data) is done externally before agents start.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from langchain_core.tools import tool

from database import Database

# ── Constants ──────────────────────────────────────────────────────────────
_RECURSION_LIMIT = 50

_SECRET    = os.environ["AI_DEVS_SECRET"]
_TASK      = os.environ.get("TASK_NAME", "foodwarehouse")
_API_URL   = os.environ["SOLUTION_URL"]
_DB_PATH   = Path(os.environ["DB_PATH"])

# ── DB singleton ───────────────────────────────────────────────────────────
_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(_DB_PATH)
    return _db


# ── Internal API helper ────────────────────────────────────────────────────
def _call(answer: dict[str, Any]) -> dict[str, Any]:
    resp = requests.post(
        _API_URL,
        json={"apikey": _SECRET, "task": _TASK, "answer": answer},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════
#  GROUP 1 – LOCAL DUCKDB
#  Used by: Recon, Demand, Mapping, Identity, Planner, Executor, Auditor
# ══════════════════════════════════════════════════════════════════════════

@tool
def db_query(sql: str) -> str:
    """Execute any SELECT query on the local DuckDB database and return results as JSON.

    Available schemas:
    - main.*        – static tables loaded at bootstrap: 'help', 'food4cities'
    - runtime.*     – tables written by agents during this run

    Use DESCRIBE <table> or SELECT * FROM information_schema.tables
    to inspect structure when needed.

    Returns: JSON array of row dicts, or {"error": "..."}.
    """
    try:
        rows = get_db().query(sql)
        return json.dumps(rows, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool
def db_store_json(table_name: str, payload: str, replace: bool = False) -> str:
    """Persist a JSON string as a structured table in the local DuckDB runtime schema.

    Accepts a JSON object or a JSON array of objects.
    Array → multiple rows (one per element).
    Single object → one row.

    Args:
        table_name: fully-qualified name, use 'runtime.<name>' prefix
                    e.g. 'runtime.city_demand', 'runtime.order_plan'
        payload:    valid JSON string
        replace:    True  → recreate table even if it already exists
                    False → skip silently if table already exists

    Returns: {"table": ..., "rows": N, "status": "ok"} or {"error": "..."}.
    """
    try:
        db = get_db()
        parsed: Any = json.loads(payload)
        records: list[dict] = parsed if isinstance(parsed, list) else [parsed]
        if not records:
            return json.dumps({"error": "payload resolved to empty list"})
        count = db.create_table_from_records(table_name, records, replace=replace)
        return json.dumps({"table": table_name, "rows": count, "status": "ok"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ══════════════════════════════════════════════════════════════════════════
#  GROUP 2 – REMOTE SQLite  (read-only, via warehouse API)
#  Used by: Recon, Mapping, Identity
# ══════════════════════════════════════════════════════════════════════════

@tool
def api_database_query(sql: str) -> str:
    """Execute a read-only SQL query against the remote SQLite database.

    Supported queries:
    - 'show tables'              – list available tables
    - 'SELECT * FROM <table>'    – read rows
    - 'PRAGMA table_info(<t>)'   – column names and types (SQLite syntax)

    Use to discover destination codes, creator identities, and
    any data needed to build the order signature.

    Returns: raw API JSON response as string, or {"error": "..."}.
    """
    try:
        result = _call({"tool": "database", "query": sql})
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ══════════════════════════════════════════════════════════════════════════
#  GROUP 3 – SIGNATURE
#  Used by: Identity
# ══════════════════════════════════════════════════════════════════════════

@tool
def api_signature_generate(payload: str) -> str:
    """Generate a SHA1 security signature using the warehouse signatureGenerator API.

    The payload must contain the user/creator fields extracted from the SQLite
    database.  Pass them as a JSON object string, e.g.:
        '{"userID": 3, "username": "jan", "email": "jan@example.com"}'

    The exact fields required are determined by exploring the SQLite schema first.

    Returns: API JSON response with the signature field, or {"error": "..."}.
    """
    try:
        data: dict = json.loads(payload) if isinstance(payload, str) else payload
        result = _call({"tool": "signatureGenerator", **data})
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ══════════════════════════════════════════════════════════════════════════
#  GROUP 4 – ORDERS  (stateful – mutates warehouse)
#  Used by: Executor (create, append); Auditor + Executor (get)
# ══════════════════════════════════════════════════════════════════════════

@tool
def api_orders_get() -> str:
    """Retrieve the current list of all orders from the warehouse API.

    Use to:
    - inspect orders created so far during execution
    - snapshot the live state for audit comparison

    Returns: API JSON response with orders list, or {"error": "..."}.
    """
    try:
        result = _call({"tool": "orders", "action": "get"})
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool
def api_orders_create(title: str, creator_id: int, destination: str, signature: str) -> str:
    """Create a single new order in the warehouse system.

    IMPORTANT: Only call this after all header fields are confirmed.
    One separate order must be created per city – never combine cities.

    Args:
        title:       human-readable order title, e.g. 'Dostawa dla Torunia'
        creator_id:  integer ID of the creator from the SQLite users table
        destination: destination code string from the SQLite cities/destinations table
        signature:   SHA1 string returned by api_signature_generate

    Returns: API JSON response with the new order ID, or {"error": "..."}.
    """
    try:
        result = _call({
            "tool":        "orders",
            "action":      "create",
            "title":       title,
            "creatorID":   creator_id,
            "destination": destination,
            "signature":   signature,
        })
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool
def api_orders_append(order_id: str, items: str) -> str:
    """Append items to an existing order using batch mode.

    Always use batch mode – send all items for the order in a single call.
    If an item already exists in the order, its quantity will be increased.

    Args:
        order_id: the order ID string returned by api_orders_create
        items:    JSON object mapping item name → quantity (int)
                  e.g. '{"chleb": 45, "woda": 120, "mlotek": 6}'

    Returns: API JSON response, or {"error": "..."}.
    """
    try:
        items_dict: dict = json.loads(items) if isinstance(items, str) else items
        result = _call({
            "tool":   "orders",
            "action": "append",
            "id":     order_id,
            "items":  items_dict,
        })
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ══════════════════════════════════════════════════════════════════════════
#  GROUP 5 – VALIDATION / AUDIT
#  Used by: Planner (execution_ready); Auditor (compare); Supervisor (done)
# ══════════════════════════════════════════════════════════════════════════

@tool
def validate_execution_ready() -> str:
    """Check whether the order plan is complete and safe to execute.

    Reads runtime.city_demand (all cities and their items) and
    runtime.order_plan (planned orders).

    Verifies:
    - every city from city_demand has exactly one row in order_plan
    - each plan row has: city, title, creator_id, destination, signature, items_json
    - no required field is null or empty

    Returns:
        {"status": "ready",     "cities": N, "issues": []} on success
        {"status": "not_ready", "cities": N, "issues": [...]} on failure
    """
    db = get_db()
    issues: list[str] = []

    try:
        demand_rows = db.query("SELECT DISTINCT city FROM runtime.city_demand")
        expected_cities = {r["city"] for r in demand_rows}
    except Exception as exc:
        return json.dumps({"status": "not_ready", "issues": [f"runtime.city_demand unavailable: {exc}"]})

    try:
        plan_rows = db.query("SELECT * FROM runtime.order_plan")
    except Exception as exc:
        return json.dumps({"status": "not_ready", "issues": [f"runtime.order_plan unavailable: {exc}"]})

    plan_cities = {r["city"] for r in plan_rows}
    missing = expected_cities - plan_cities
    if missing:
        issues.append(f"Cities missing from plan: {sorted(missing)}")

    required = ["city", "title", "creator_id", "destination", "signature", "items_json"]
    for row in plan_rows:
        for field in required:
            if not row.get(field):
                issues.append(f"Null/empty '{field}' for city '{row.get('city', '?')}'")

    status = "ready" if not issues else "not_ready"
    return json.dumps({
        "status":  status,
        "cities":  len(expected_cities),
        "planned": len(plan_rows),
        "issues":  issues,
    })


@tool
def compare_expected_vs_actual() -> str:
    """Compare planned orders (runtime.order_plan) with live orders from the warehouse API.

    Checks:
    - order count matches city count
    - each city's order exists with the correct destination
    - item names and quantities match exactly (no missing, no excess)

    Returns:
        {"status": "pass", "details": [...]} when everything matches
        {"status": "fail", "issues": [...], "details": [...]} when mismatches found
    """
    db = get_db()
    issues: list[str] = []

    try:
        plan_rows = db.query("SELECT * FROM runtime.order_plan")
    except Exception as exc:
        return json.dumps({"status": "fail", "issues": [f"runtime.order_plan unavailable: {exc}"]})

    try:
        api_resp  = _call({"tool": "orders", "action": "get"})
        # API may nest orders under a key – try common shapes
        raw = api_resp
        if isinstance(raw, dict):
            actual_orders = raw.get("orders") or raw.get("message") or raw.get("data") or raw
        if isinstance(actual_orders, str):
            actual_orders = json.loads(actual_orders)
        if not isinstance(actual_orders, list):
            actual_orders = [actual_orders]
    except Exception as exc:
        return json.dumps({"status": "fail", "issues": [f"api_orders_get failed: {exc}"]})

    if len(actual_orders) != len(plan_rows):
        issues.append(
            f"Order count mismatch: expected {len(plan_rows)}, actual {len(actual_orders)}"
        )

    actual_by_dest: dict[str, dict] = {
        str(o.get("destination", o.get("dest", ""))): o
        for o in actual_orders
    }

    details: list[dict] = []
    for row in plan_rows:
        city = row["city"]
        dest = str(row.get("destination", ""))
        actual = actual_by_dest.get(dest)

        if actual is None:
            issues.append(f"[{city}] No actual order for destination='{dest}'")
            details.append({"city": city, "status": "missing_order"})
            continue

        expected_items: dict = json.loads(row.get("items_json") or "{}")
        actual_items:   dict = {
            i["name"]: int(i.get("quantity", i.get("qty", 0)))
            for i in actual.get("items", [])
        }

        city_diffs: list[str] = []
        for name, qty in expected_items.items():
            got = actual_items.get(name, 0)
            if got != qty:
                city_diffs.append(f"{name}: expected {qty}, got {got}")
        for name, qty in actual_items.items():
            if name not in expected_items:
                city_diffs.append(f"{name}: unexpected item (qty={qty})")

        if city_diffs:
            issues.extend(f"[{city}] {d}" for d in city_diffs)
            details.append({"city": city, "status": "mismatch", "diffs": city_diffs})
        else:
            details.append({"city": city, "status": "ok"})

    return json.dumps({
        "status":  "pass" if not issues else "fail",
        "issues":  issues,
        "details": details,
    }, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════
#  GROUP 6 – FINALIZATION
#  Used by: Supervisor only
# ══════════════════════════════════════════════════════════════════════════

@tool
def api_done() -> str:
    """Submit the final verification to the warehouse API (tool=done).

    ONLY call this after compare_expected_vs_actual returns status='pass'.
    If all orders are correct, Centrala will respond with the flag.

    Returns: API JSON response (including flag on success), or {"error": "..."}.
    """
    try:
        result = _call({"tool": "done"})
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})

import json
import os
from pathlib import Path
from typing import Any, Optional

from langchain_core.tools import tool

from libs.central_client import _post_to_central, _scan_flag_in_response
from libs.loggers import agent_logger
from libs.database import Database

# ── Constants ─────────────────────────────────────────────────────────────
_RECURSION_LIMIT = 50

AI_DEVS_SECRET = os.environ["AI_DEVS_SECRET"]
TASK_NAME = os.environ["TASK_NAME"]
SOLUTION_URL = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
DB_PATH = Path(os.environ["DB_PATH"])
DB_RUNTIME_PATH = Path(os.environ["DB_RUNTIME_PATH"])

# ── DB singletons ─────────────────────────────────────────────────────────

_static_db: Database | None = None
_runtime_db: Database | None = None


def get_static_db() -> Database:
    global _static_db
    if _static_db is None:
        _static_db = Database(DB_PATH)
    return _static_db


def get_runtime_db() -> Database:
    global _runtime_db
    if _runtime_db is None:
        _runtime_db = Database(DB_RUNTIME_PATH)
    return _runtime_db


# ══════════════════════════════════════════════════════════════════════════
# GROUP 1 — LOCAL DUCKDB (static, read-only)
# Used by: Recon, Demand, Mapping, Identity, Planner
# ══════════════════════════════════════════════════════════════════════════


@tool
def static_db_query(sql: str) -> str:
    """Execute a SELECT query on the local static DuckDB database and return results as JSON.

    This database is read-only — it contains tables loaded at bootstrap:
      - 'food4cities'  — demand per city (city, item, quantity)
      - 'get_help'     — raw API help text stored as single JSON column 'data'

    Use DESCRIBE <table> to inspect columns.
    Use SHOW TABLES to list available tables.
    Always use SELECT — never INSERT, UPDATE, DROP or DDL.

    Returns: JSON array of row objects, or an error message string.
    """
    try:
        db = get_static_db()
        rows = db.query(sql)
        return json.dumps(rows, ensure_ascii=False)
    except Exception as e:
        return f"ERROR: {e}"


# ══════════════════════════════════════════════════════════════════════════
# GROUP 2 — LOCAL DUCKDB (runtime, read + write)
# Used by: Recon, Demand, Mapping, Identity, Planner, Executor, Auditor
# ══════════════════════════════════════════════════════════════════════════


@tool
def runtime_db_query(sql: str) -> str:
    """Execute a SELECT query on the local runtime DuckDB database and return results as JSON.

    This database is the agent workspace — tables are created and populated during the run.
    Common tables written by agents:
      - city_demand          — normalized demand per city and item
      - destination_map      — city → destination code mapping
      - identity_map         — city → creatorID + signature mapping
      - order_plan           — finalized plan: one row per city with all order fields
      - order_plan_items     — individual items per planned order
      - execution_log        — API responses from orders.create / orders.append
      - audit_report         — comparison of planned vs actual order state

    Use DESCRIBE <table> to inspect columns.
    Use SHOW TABLES to list available tables.

    Returns: JSON array of row objects, or an error message string.
    """
    try:
        db = get_runtime_db()
        rows = db.query(sql)
        return json.dumps(rows, ensure_ascii=False)
    except Exception as e:
        return f"ERROR: {e}"


@tool
def runtime_db_store_records(table_name: str, records_json: str, replace: bool = False) -> str:
    """Store a list of records into a runtime DuckDB table.

    Args:
        table_name:   Target table name (no schema prefix needed — always writes to runtime DB).
                      Examples: 'city_demand', 'destination_map', 'order_plan', 'execution_log'
        records_json: JSON array string of row objects. All objects must share the same keys.
                      Example: '[{"city": "Warszawa", "item": "chleb", "qty": 100}]'
        replace:      If True, drops and recreates the table. If False, creates only if not exists.

    Returns: Confirmation string with row count, or an error message.
    """
    try:
        db = get_runtime_db()
        records: list[dict[str, Any]] = json.loads(records_json)
        if not isinstance(records, list) or not records:
            return "ERROR: records_json must be a non-empty JSON array"
        count = db.create_table_from_records(table_name, records, replace=replace)
        return f"OK: stored {count} rows into runtime table '{table_name}'"
    except Exception as e:
        return f"ERROR: {e}"


@tool
def runtime_db_append_records(table_name: str, records_json: str) -> str:
    """Append rows to an existing runtime DuckDB table.

    Use this when the table already exists and you want to add more rows without replacing it.
    All records must match the existing table schema.

    Args:
        table_name:   Existing runtime table name. Example: 'execution_log'
        records_json: JSON array string of row objects matching table schema.

    Returns: Confirmation string with inserted row count, or an error message.
    """
    try:
        db = get_runtime_db()
        records: list[dict[str, Any]] = json.loads(records_json)
        if not isinstance(records, list) or not records:
            return "ERROR: records_json must be a non-empty JSON array"
        count = db.append_records(table_name, records)
        return f"OK: appended {count} rows to runtime table '{table_name}'"
    except Exception as e:
        return f"ERROR: {e}"


# ══════════════════════════════════════════════════════════════════════════
# GROUP 3 — REMOTE SQLITE (read-only via API)
# Used by: Recon, Mapping, Identity
# ══════════════════════════════════════════════════════════════════════════


@tool
def api_database_query(query: str) -> str:
    """Execute a SELECT query or 'show tables' against the remote read-only SQLite database via API.

    Use this to discover the database schema and read authorization data needed to build orders.
    Allowed operations: 'show tables', SELECT queries only.

    Examples:
        api_database_query("show tables")
        api_database_query("SELECT * FROM users LIMIT 5")
        api_database_query("DESCRIBE employees")

    Returns: API response as JSON string, or an error message.
    """
    try:
        result, _ = _post_to_central({"tool": "database", "query": query})
        return result
    except Exception as e:
        return f"ERROR: {e}"


# ══════════════════════════════════════════════════════════════════════════
# GROUP 4 — SIGNATURE GENERATOR
# Used by: Identity
# ══════════════════════════════════════════════════════════════════════════


@tool
def api_signature_generate(params_json: str) -> str:
    """Generate a SHA1 security signature for an order via the signatureGenerator API.

    The signature is built from user data stored in the remote SQLite database.
    You must first identify the correct user (creatorID) and their relevant fields
    from the database before calling this tool.

    Args:
        params_json: JSON object string with the fields required by signatureGenerator.
                     Must include: "action", "login", "birthday", "destination".
                     Example: '{"action": "generate", "login": "jkowalski", "birthday": "1971-01-01", "destination": 991828}'

    Returns: API response containing the generated signature string, or an error message.
    """
    try:
        params: dict[str, Any] = json.loads(params_json)
        payload = {"tool": "signatureGenerator", **params}
        result, _ = _post_to_central(payload)
        return result
    except Exception as e:
        return f"ERROR: {e}"


# ══════════════════════════════════════════════════════════════════════════
# GROUP 5 — ORDERS API
# Used by: Executor, Auditor
# ══════════════════════════════════════════════════════════════════════════


@tool
def api_orders_get() -> str:
    """Retrieve the current list of all orders from the warehouse API.

    Use this to:
      - inspect existing orders before creating new ones
      - verify order state after create/append operations
      - audit actual vs planned order content

    Returns: JSON string with all current orders, or an error message.
    """
    try:
        result, _ = _post_to_central({"tool": "orders", "action": "get"})
        return result
    except Exception as e:
        return f"ERROR: {e}"


@tool
def api_orders_create(title: str, creator_id: int, destination: str, signature: str) -> str:
    """Create a new order in the warehouse API.

    Only call this after the full order plan has been validated in the runtime DB.
    You must have: title, creatorID, destination code, and a valid signature.

    Args:
        title:       Human-readable order title. Example: 'Dostawa dla Torunia'
        creator_id:  Integer user ID from the SQLite database.
        destination: Destination code string for the target city. Example: '1234'
        signature:   SHA1 signature string from signatureGenerator.

    Returns: API response with the new order ID, or an error message.
    """
    try:
        result, _ = _post_to_central({
            "tool": "orders",
            "action": "create",
            "title": title,
            "creatorID": creator_id,
            "destination": destination,
            "signature": signature,
        })
        return result
    except Exception as e:
        return f"ERROR: {e}"


@tool
def api_orders_append(order_id: str, items_json: str) -> str:
    """Append items to an existing order in the warehouse API (batch mode).

    Use this after api_orders_create to populate the order with required goods.
    Supports batch mode — pass multiple items at once as a JSON object.

    If an item already exists in the order, its quantity will be increased (no duplicate created).

    Args:
        order_id:   Order ID returned by api_orders_create.
        items_json: JSON object string mapping item names to quantities.
                    Example: '{"chleb": 45, "woda": 120, "mlotek": 6}'

    Returns: API response confirming the append, or an error message.
    """
    try:
        items: dict[str, int] = json.loads(items_json)
        result, _ = _post_to_central({
            "tool": "orders",
            "action": "append",
            "id": order_id,
            "items": items,
        })
        return result
    except Exception as e:
        return f"ERROR: {e}"


# ══════════════════════════════════════════════════════════════════════════
# GROUP 6 — CONTROL TOOLS
# Used by: Supervisor, Auditor
# ══════════════════════════════════════════════════════════════════════════


@tool
def api_reset() -> str:
    """Reset all orders to the initial state via the warehouse API.

    Use this when orders are in an inconsistent state and need to be rebuilt from scratch.
    WARNING: This deletes all existing orders — use only after confirming with the Supervisor.

    Returns: API response confirming the reset, or an error message.
    """
    try:
        result, _ = _post_to_central({"tool": "reset"})
        return result
    except Exception as e:
        return f"ERROR: {e}"


@tool
def api_done() -> str:
    """Submit the final 'done' signal to the warehouse API for verification.

    Only call this after the Auditor has confirmed that:
      - all required cities have an order
      - each order has the correct destination, creatorID, and signature
      - each order contains exactly the required items (no missing, no extra)

    If the solution is correct, the API will return a success flag.
    After calling this tool, pass the response to scan_flag to extract and log the flag.

    Returns: API response string.
    """
    try:
        result, _ = _post_to_central({"tool": "done"})
        return result
    except Exception as e:
        return f"ERROR: {e}"



@tool
def scan_flag(text: str) -> Optional[str]:
    """Search for a real success flag matching the pattern {FLG:XXXXX} in the given text.

    The flag must start with an alphanumeric character after 'FLG:' — placeholder text
    like {FLG:...} is ignored.

    Call this tool on the server's api_done() response to verify task completion.

    Args:
        text: Raw response string from api_done().

    Returns: The flag string if found (e.g. '{FLG:abc123}'), or None.
    """
    flag = _scan_flag_in_response(text)
    if flag:
        agent_logger.info(f"[scan_flag] Flag found: {flag}")
        return flag
    agent_logger.info(f"[scan_flag] no flag in text={text[:200]}")
    return None

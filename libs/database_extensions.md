# Additional generic methods for `Database`

Below is the full list of newly added generic methods. The original methods were kept unchanged. The additions focus on schema management, table/view lifecycle, record insertion, introspection, export, transactions, and identifier safety.

## File loading

### `load_json_file(table_name: str, file_path: Path, replace: bool = False) -> int`
Loads a single JSON file into a table.

**Purpose**
Use this when you want to import one JSON file directly instead of scanning a whole directory.

**Example**
```python
from pathlib import Path

db.load_json_file("raw_input", Path("data/input.json"), replace=True)
```

### `load_csv_file(table_name: str, file_path: Path, replace: bool = False) -> int`
Loads a single CSV file into a table.

**Purpose**
Useful for one-off imports and cleaner pipelines when only one CSV file is needed.

**Example**
```python
from pathlib import Path

db.load_csv_file("users", Path("data/users.csv"), replace=True)
```

## Schema management

### `create_schema(schema_name: str) -> None`
Creates a schema if it does not exist.

**Purpose**
Helps separate static, runtime, audit, or temporary data into logical namespaces.

**Example**
```python
db.create_schema("runtime")
```

### `drop_schema(schema_name: str, cascade: bool = False) -> None`
Drops a schema.

**Purpose**
Useful for resetting a workspace namespace. With `cascade=True`, all objects inside the schema are removed as well.

**Example**
```python
db.drop_schema("runtime", cascade=True)
```

## Table and view lifecycle

### `table_exists(table_name: str) -> bool`
Checks whether a table exists.

**Purpose**
Useful before creating, replacing, or appending to a table.

**Example**
```python
if db.table_exists("runtime.jobs"):
    print("table exists")
```

### `view_exists(view_name: str) -> bool`
Checks whether a view exists.

**Purpose**
Useful when derived read-only datasets are managed through views.

**Example**
```python
if not db.view_exists("runtime.active_jobs"):
    ...
```

### `drop_table(table_name: str, if_exists: bool = True) -> None`
Drops a table.

**Purpose**
Useful for removing stale intermediate tables.

**Example**
```python
db.drop_table("runtime.staging_results")
```

### `drop_view(view_name: str, if_exists: bool = True) -> None`
Drops a view.

**Purpose**
Useful for cleaning up derived objects.

**Example**
```python
db.drop_view("runtime.latest_results")
```

### `truncate_table(table_name: str) -> None`
Removes all rows from a table while keeping the schema.

**Purpose**
Useful for reusable staging tables.

**Example**
```python
db.truncate_table("runtime.queue")
```

### `create_table_as(table_name: str, sql: str, replace: bool = False) -> int`
Creates a table from a SELECT query.

**Purpose**
Materializes snapshots, filtered datasets, joins, and reusable intermediate outputs.

**Example**
```python
db.create_table_as(
    "runtime.high_value_users",
    "SELECT * FROM users WHERE total_spend > 1000",
    replace=True,
)
```

### `create_view(view_name: str, sql: str, replace: bool = False) -> None`
Creates a view from a SELECT query.

**Purpose**
Useful for reusable read-only transformations that should stay in sync with source tables.

**Example**
```python
db.create_view(
    "runtime.active_users",
    "SELECT * FROM users WHERE is_active = true",
    replace=True,
)
```

## Record insertion

### `create_table_from_records(table_name: str, records: list[dict[str, Any]], replace: bool = False) -> int`
Creates a table from a list of dictionaries.

**Purpose**
Useful when data was produced in memory, for example by an API client or a transformation step.

**Example**
```python
rows = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
]
db.create_table_from_records("runtime.people", rows, replace=True)
```

### `append_records(table_name: str, records: list[dict[str, Any]]) -> int`
Appends a list of dictionaries to an existing table.

**Purpose**
Useful for adding runtime batches into already created tables.

**Example**
```python
db.append_records("runtime.people", [{"id": 3, "name": "Carol"}])
```

### `insert_dict(table_name: str, record: dict[str, Any]) -> int`
Inserts one dictionary into an existing table.

**Purpose**
Convenience method for single-row inserts.

**Example**
```python
db.insert_dict("runtime.people", {"id": 4, "name": "Dave"})
```

## Query execution

### `execute(sql: str) -> None`
Executes SQL without returning rows.

**Purpose**
Useful for DDL, maintenance commands, and write operations.

**Example**
```python
db.execute("ANALYZE")
```

### `execute_params(sql: str, params: list) -> None`
Executes a parameterized SQL statement without returning rows.

**Purpose**
Useful for inserts, updates, deletes, and other write operations with bound values.

**Example**
```python
db.execute_params(
    "INSERT INTO runtime.logs(level, message) VALUES (?, ?)",
    ["INFO", "pipeline started"],
)
```

## Introspection

### `columns(table_name: str) -> list[str]`
Returns column names only.

**Purpose**
Useful when building dynamic SQL or validating table compatibility.

**Example**
```python
print(db.columns("users"))
```

### `count(table_name: str) -> int`
Returns the row count of a table.

**Purpose**
Useful for quick validation and assertions.

**Example**
```python
print(db.count("users"))
```

### `sample(table_name: str, limit: int = 10) -> list[dict[str, Any]]`
Returns the first N rows from a table.

**Purpose**
Useful for quick inspection and debugging.

**Example**
```python
print(db.sample("users", limit=5))
```

## Export

### `export_query_csv(sql: str, file_path: Path, header: bool = True) -> Path`
Exports a query result to CSV.

**Purpose**
Useful for debugging, sharing, or passing derived data to other tools.

**Example**
```python
from pathlib import Path

db.export_query_csv(
    "SELECT * FROM users WHERE is_active = true",
    Path("output/active_users.csv"),
)
```

### `export_table_csv(table_name: str, file_path: Path, header: bool = True) -> Path`
Exports a full table to CSV.

**Purpose**
Convenience wrapper for exporting complete tables.

**Example**
```python
from pathlib import Path

db.export_table_csv("users", Path("output/users.csv"))
```

## Transactions

### `begin() -> None`
Starts a transaction.

**Purpose**
Useful when multiple writes should succeed or fail together.

**Example**
```python
db.begin()
try:
    db.insert_dict("runtime.logs", {"level": "INFO", "message": "start"})
    db.insert_dict("runtime.logs", {"level": "INFO", "message": "done"})
    db.commit()
except Exception:
    db.rollback()
    raise
```

### `commit() -> None`
Commits the current transaction.

**Purpose**
Finalizes a successful transactional write sequence.

### `rollback() -> None`
Rolls back the current transaction.

**Purpose**
Reverts a failed transactional write sequence.

## Identifier helpers

### `quote_identifier(name: str) -> str`
Safely quotes SQL identifiers.

**Purpose**
Useful for schema-qualified names and names containing special characters.

**Example**
```python
safe_name = db.quote_identifier("runtime.users")
```

### `normalize_identifier(name: str) -> str`
Normalizes a string into a SQL-friendly identifier.

**Purpose**
Useful when table or column names originate from filenames, user input, or external systems.

**Example**
```python
print(db.normalize_identifier("Raw API Response 01"))
# raw_api_response_01
```

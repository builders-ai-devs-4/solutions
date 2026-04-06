from pathlib import Path
from typing import Any
import json
import re
import duckdb


class Database:
    """
    Generic DuckDB database for loading CSV and JSON files into named tables.
    Schema is inferred automatically from file contents.
    Source filename is always stored as an extra column.
    """

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)

    # ── JSON ──────────────────────────────────────────────────────────────────

    def load_json_dir_single_table(self, table_name: str, directory: Path) -> int:
        """
        Load all *.json files from a directory into ONE table.
        Use when all files share the same schema.
        Stores source filename as extra column.
        """
        glob = (directory / "*.json").as_posix()
        self.conn.sql(f"""
        CREATE TABLE IF NOT EXISTS {table_name} AS
        SELECT *
        FROM read_json_auto('{glob}', filename=true)
        """)
        return self._count(table_name)

    def load_json_dir_multi_table(self, directory: Path) -> dict[str, int]:
        """
        Load each *.json file from a directory into its OWN table.
        Table name = file stem (e.g. orders.json → table 'orders').
        Use when files have different schemas.
        Stores source filename as extra column.
        """
        counts = {}
        for file in sorted(directory.glob("*.json")):
            table_name = file.stem
            self.conn.sql(f"""
            CREATE TABLE IF NOT EXISTS {table_name} AS
            SELECT *
            FROM read_json_auto('{file.as_posix()}', filename=true)
            """)
            counts[table_name] = self._count(table_name)
        return counts

    def load_json_file(self, table_name: str, file_path: Path, replace: bool = False) -> int:
        """
        Load a single JSON file into a table.

        Use this when you want to import one file directly instead of scanning
        a whole directory. Schema is inferred automatically by DuckDB.
        """
        table_name = self.quote_identifier(table_name)
        file_path = file_path.as_posix()
        create_clause = "CREATE OR REPLACE TABLE" if replace else "CREATE TABLE IF NOT EXISTS"
        self.conn.sql(f"""
        {create_clause} {table_name} AS
        SELECT *
        FROM read_json_auto('{file_path}', filename=true)
        """)
        return self._count(table_name)

    # ── CSV ───────────────────────────────────────────────────────────────────

    def load_csv_dir_single_table(self, table_name: str, directory: Path) -> int:
        """
        Load all *.csv files from a directory into ONE table.
        Use when all files share the same schema.
        Stores source filename as extra column.
        """
        glob = (directory / "*.csv").as_posix()
        self.conn.sql(f"""
        CREATE TABLE IF NOT EXISTS {table_name} AS
        SELECT *
        FROM read_csv_auto('{glob}', header=true, filename=true)
        """)
        return self._count(table_name)

    def load_csv_dir_multi_table(self, directory: Path) -> dict[str, int]:
        """
        Load each *.csv file from a directory into its OWN table.
        Table name = file stem (e.g. users.csv → table 'users').
        Use when files have different schemas.
        Stores source filename as extra column.
        """
        counts = {}
        for file in sorted(directory.glob("*.csv")):
            table_name = file.stem
            self.conn.sql(f"""
            CREATE TABLE IF NOT EXISTS {table_name} AS
            SELECT *
            FROM read_csv_auto('{file.as_posix()}', header=true, filename=true)
            """)
            counts[table_name] = self._count(table_name)
        return counts

    def load_csv_file(self, table_name: str, file_path: Path, replace: bool = False) -> int:
        """
        Load a single CSV file into a table.

        Use this when you want to import one file directly instead of scanning
        a whole directory. The header row is assumed to be present.
        """
        table_name = self.quote_identifier(table_name)
        file_path = file_path.as_posix()
        create_clause = "CREATE OR REPLACE TABLE" if replace else "CREATE TABLE IF NOT EXISTS"
        self.conn.sql(f"""
        {create_clause} {table_name} AS
        SELECT *
        FROM read_csv_auto('{file_path}', header=true, filename=true)
        """)
        return self._count(table_name)

    # ── Schema management ─────────────────────────────────────────────────────

    def create_schema(self, schema_name: str) -> None:
        """
        Create a schema if it does not already exist.

        Schemas are useful for separating logical areas such as static data,
        runtime caches, audit tables, or temporary workspaces.
        """
        schema_name = self.quote_identifier(schema_name)
        self.conn.sql(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")

    def drop_schema(self, schema_name: str, cascade: bool = False) -> None:
        """
        Drop a schema.

        Set cascade=True to remove all contained objects as well.
        This is useful for resetting a workspace namespace.
        """
        schema_name = self.quote_identifier(schema_name)
        cascade_sql = " CASCADE" if cascade else ""
        self.conn.sql(f"DROP SCHEMA IF EXISTS {schema_name}{cascade_sql}")

    # ── Table and view utilities ──────────────────────────────────────────────

    def table_exists(self, table_name: str) -> bool:
        """
        Check whether a table exists.

        Fully qualified names such as schema.table are supported.
        """
        parts = self._split_qualified_name(table_name)
        if len(parts) == 2:
            schema_name, name = parts
            result = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = ? AND table_name = ?
                """,
                [schema_name, name],
            ).fetchone()[0]
        else:
            name = parts[0]
            result = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = ?
                """,
                [name],
            ).fetchone()[0]
        return result > 0

    def view_exists(self, view_name: str) -> bool:
        """
        Check whether a view exists.

        Fully qualified names such as schema.view are supported.
        """
        parts = self._split_qualified_name(view_name)
        if len(parts) == 2:
            schema_name, name = parts
            result = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.views
                WHERE table_schema = ? AND table_name = ?
                """,
                [schema_name, name],
            ).fetchone()[0]
        else:
            name = parts[0]
            result = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.views
                WHERE table_name = ?
                """,
                [name],
            ).fetchone()[0]
        return result > 0

    def drop_table(self, table_name: str, if_exists: bool = True) -> None:
        """
        Drop a table.

        Use this to remove intermediate or stale tables that are no longer
        needed.
        """
        table_name = self.quote_identifier(table_name)
        if_exists_sql = " IF EXISTS" if if_exists else ""
        self.conn.sql(f"DROP TABLE{if_exists_sql} {table_name}")

    def drop_view(self, view_name: str, if_exists: bool = True) -> None:
        """
        Drop a view.

        Use this to remove derived views that are no longer needed.
        """
        view_name = self.quote_identifier(view_name)
        if_exists_sql = " IF EXISTS" if if_exists else ""
        self.conn.sql(f"DROP VIEW{if_exists_sql} {view_name}")

    def truncate_table(self, table_name: str) -> None:
        """
        Remove all rows from a table while keeping the table structure.

        This is useful when you want to reuse a staging table across multiple
        runs.
        """
        table_name = self.quote_identifier(table_name)
        self.conn.sql(f"DELETE FROM {table_name}")

    def create_table_as(self, table_name: str, sql: str, replace: bool = False) -> int:
        """
        Create a table from the result of a SELECT query.

        This is handy for materializing filtered datasets, snapshots, joins,
        or reusable intermediate results.
        """
        table_name = self.quote_identifier(table_name)
        create_clause = "CREATE OR REPLACE TABLE" if replace else "CREATE TABLE IF NOT EXISTS"
        self.conn.sql(f"{create_clause} {table_name} AS {sql}")
        return self._count(table_name)

    def create_view(self, view_name: str, sql: str, replace: bool = False) -> None:
        """
        Create a view from a SELECT query.

        Views are useful for reusable read-only transformations that should
        always reflect the current source tables.
        """
        view_name = self.quote_identifier(view_name)
        create_clause = "CREATE OR REPLACE VIEW" if replace else "CREATE VIEW IF NOT EXISTS"
        self.conn.sql(f"{create_clause} {view_name} AS {sql}")

    # ── Record insertion ──────────────────────────────────────────────────────

    def create_table_from_records(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        replace: bool = False,
    ) -> int:
        """
        Create a table from a list of dictionaries.

        This is useful when data is produced in memory, for example by API
        responses, parsing steps, or Python transformations.
        """
        if not records:
            raise ValueError("records must not be empty")

        table_name = self.quote_identifier(table_name)
        rows_json = json.dumps(records)
        create_clause = "CREATE OR REPLACE TABLE" if replace else "CREATE TABLE IF NOT EXISTS"
        self.conn.sql(f"""
        {create_clause} {table_name} AS
        SELECT *
        FROM read_json_auto('{rows_json}', format='array')
        """)
        return self._count(table_name)

    def append_records(self, table_name: str, records: list[dict[str, Any]]) -> int:
        """
        Append a list of dictionaries to an existing table.

        All records are expected to match the target table schema. The return
        value is the number of inserted rows.
        """
        if not records:
            return 0

        columns = list(records[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        quoted_columns = ", ".join(self.quote_identifier(col) for col in columns)
        table_name = self.quote_identifier(table_name)
        sql = f"INSERT INTO {table_name} ({quoted_columns}) VALUES ({placeholders})"
        values = [tuple(record.get(col) for col in columns) for record in records]
        self.conn.executemany(sql, values)
        return len(records)

    def insert_dict(self, table_name: str, record: dict[str, Any]) -> int:
        """
        Insert a single dictionary into an existing table.

        This is a convenience wrapper around append_records for one row.
        """
        return self.append_records(table_name, [record])

    # ── Query helpers ─────────────────────────────────────────────────────────

    def query(self, sql: str) -> list[dict[str, Any]]:
        """
        Execute arbitrary SQL and return list of dicts.
        Example:
        results = db.query('''
        SELECT u.name, o.amount
        FROM users u JOIN orders o ON u.id = o.user_id
        ''')

        """
        result = self.conn.sql(sql)
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def query_params(self, sql: str, params: list) -> list[dict[str, Any]]:
        """
        Execute a parameterized SQL query and return a list of dictionaries.

        Use this when values should be passed separately from the SQL string.
        """
        result = self.conn.execute(sql, params)
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def execute(self, sql: str) -> None:
        """
        Execute SQL that does not need to return rows.

        This is useful for DDL statements or bulk operations where the result
        set is not needed.
        """
        self.conn.execute(sql)

    def execute_params(self, sql: str, params: list) -> None:
        """
        Execute a parameterized SQL statement that does not return rows.

        This is useful for inserts, updates, deletes, and DDL-like commands
        with bound values.
        """
        self.conn.execute(sql, params)

    # ── Introspection ─────────────────────────────────────────────────────────

    def tables(self) -> list[str]:
        """Return list of all table names in the database."""
        return [row[0] for row in self.conn.sql("SHOW TABLES").fetchall()]

    def schema(self, table_name: str) -> list[dict[str, str]]:
        """Return column names and types for a given table."""
        result = self.conn.sql(f"DESCRIBE {table_name}")
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def columns(self, table_name: str) -> list[str]:
        """
        Return only the column names for a table.

        This is a lightweight helper built on top of schema().
        """
        return [row["column_name"] for row in self.schema(table_name)]

    def count(self, table_name: str) -> int:
        """
        Return the number of rows in a table.

        This is the public counterpart of the internal _count helper.
        """
        return self._count(table_name)

    def sample(self, table_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the first N rows from a table.

        This is useful for quick inspection during development or debugging.
        """
        table_name = self.quote_identifier(table_name)
        return self.query(f"SELECT * FROM {table_name} LIMIT {int(limit)}")

    # ── Export ────────────────────────────────────────────────────────────────

    def export_query_csv(self, sql: str, file_path: Path, header: bool = True) -> Path:
        """
        Export a query result to a CSV file.

        This is useful for debugging, sharing intermediate results, or passing
        derived data to other tools.
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        header_sql = "true" if header else "false"
        self.conn.sql(
            f"COPY ({sql}) TO '{file_path.as_posix()}' (FORMAT CSV, HEADER {header_sql})"
        )
        return file_path

    def export_table_csv(self, table_name: str, file_path: Path, header: bool = True) -> Path:
        """
        Export a full table to a CSV file.

        This is a convenience wrapper around export_query_csv.
        """
        table_name = self.quote_identifier(table_name)
        return self.export_query_csv(f"SELECT * FROM {table_name}", file_path, header=header)

    # ── Transactions ──────────────────────────────────────────────────────────

    def begin(self) -> None:
        """
        Start a transaction explicitly.

        Use this when multiple write operations should succeed or fail as a
        single unit.
        """
        self.conn.execute("BEGIN")

    def commit(self) -> None:
        """
        Commit the current transaction.

        Call this after a successful batch of related write operations.
        """
        self.conn.execute("COMMIT")

    def rollback(self) -> None:
        """
        Roll back the current transaction.

        Call this when a write sequence should be discarded due to an error.
        """
        self.conn.execute("ROLLBACK")

    # ── Identifier helpers ────────────────────────────────────────────────────

    def quote_identifier(self, name: str) -> str:
        """
        Quote a table, schema, view, or column identifier safely.

        Dots are treated as qualified-name separators, so schema.table and
        schema.view are supported.
        """
        parts = self._split_qualified_name(name)
        return ".".join(f'"{part.replace(chr(34), chr(34) * 2)}"' for part in parts)

    def normalize_identifier(self, name: str) -> str:
        """
        Normalize a string into a SQL-friendly identifier.

        The result is lowercased and non-alphanumeric characters are replaced
        with underscores.
        """
        normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        if not normalized:
            raise ValueError("identifier must not be empty")
        return normalized

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _split_qualified_name(self, name: str) -> list[str]:
        return [part.strip() for part in name.split(".") if part.strip()]

    def _count(self, table_name: str) -> int:
        table_name = self.quote_identifier(table_name)
        return self.conn.sql(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

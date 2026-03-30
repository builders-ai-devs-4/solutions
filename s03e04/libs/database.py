from pathlib import Path
from typing import Any
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
            SELECT *, filename
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
                SELECT *, '{file.name}' AS filename
                FROM read_json_auto('{file.as_posix()}')
            """)
            counts[table_name] = self._count(table_name)
        return counts

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
            SELECT *, filename
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
                SELECT *, '{file.name}' AS filename
                FROM read_csv_auto('{file.as_posix()}', header=true)
            """)
            counts[table_name] = self._count(table_name)
        return counts

    # ── Utils ─────────────────────────────────────────────────────────────────

    def query(self, sql: str) -> list[dict[str, Any]]:
        """Execute arbitrary SQL and return list of dicts."""
        result = self.conn.sql(sql)
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def tables(self) -> list[str]:
        """Return list of all table names in the database."""
        return [row[0] for row in self.conn.sql("SHOW TABLES").fetchall()]
    
    def schema(self, table_name: str) -> list[dict[str, str]]:
        """Return column names and types for a given table."""
        result = self.conn.sql(f"DESCRIBE {table_name}")
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def _count(self, table_name: str) -> int:
        return self.conn.sql(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
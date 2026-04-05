from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import json
import sqlite3


@dataclass
class ParsedDocument:
    """
    Normalized representation of one file before it is saved.
    """

    path: str
    filename: str
    doc_type: str
    title: str
    body: str
    source_text: str
    metadata_json: str
    file_size: int
    modified_ts: float


class Database:
    """
    Generic SQLite + FTS5 database for loading Markdown, text, and JSON files.

    Full document text is stored in a regular table.
    FTS5 is used only for fast full-text search over title and body.
    Search results can return the full indexed content immediately,
    without reading files from disk again.
    """

    def __init__(self, db_path: Path) -> None:
        """
        Open the SQLite database and initialize schema objects.
        """
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                source_text TEXT NOT NULL,
                metadata_json TEXT,
                file_size INTEGER NOT NULL,
                modified_ts REAL NOT NULL,
                indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title,
                body,
                content='documents',
                content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            );

            CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
              INSERT INTO documents_fts(rowid, title, body)
              VALUES (new.id, new.title, new.body);
            END;

            CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
              INSERT INTO documents_fts(documents_fts, rowid, title, body)
              VALUES('delete', old.id, old.title, old.body);
            END;

            CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
              INSERT INTO documents_fts(documents_fts, rowid, title, body)
              VALUES('delete', old.id, old.title, old.body);
              INSERT INTO documents_fts(rowid, title, body)
              VALUES (new.id, new.title, new.body);
            END;

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL,
                line_no INTEGER NOT NULL,
                from_city TEXT NOT NULL,
                item TEXT NOT NULL,
                to_city TEXT NOT NULL,
                raw_line TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_document_id ON transactions(document_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_from_city ON transactions(from_city);
            CREATE INDEX IF NOT EXISTS idx_transactions_to_city ON transactions(to_city);
            CREATE INDEX IF NOT EXISTS idx_transactions_item ON transactions(item);
            """
        )

    # ── Directory loading ─────────────────────────────────────────────────────

    def load_documents_dir(self, directory: Path) -> int:
        """
        Load all supported files from a directory into one documents table.

        Supported extensions: *.md, *.txt, *.json.
        Files removed from disk are also removed from the database.
        Returns the total number of indexed documents.
        """
        directory = directory.resolve()
        existing_paths = {str(path.resolve()) for path in self._iter_supported_files(directory)}
        db_paths = {row['path'] for row in self.conn.execute("SELECT path FROM documents").fetchall()}

        for stale_path in db_paths - existing_paths:
            self.conn.execute("DELETE FROM documents WHERE path = ?", (stale_path,))

        for file_path in self._iter_supported_files(directory):
            self._upsert_document(file_path)

        self.conn.commit()
        return self._count("documents")

    # ── Search ────────────────────────────────────────────────────────────────

    def search_documents(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search indexed documents with FTS5 and return full rows.

        The result already includes the full document body stored in SQLite,
        plus an FTS snippet and BM25 score.
        """
        result = self.conn.execute(
            """
            SELECT
                d.id,
                d.path,
                d.filename,
                d.doc_type,
                d.title,
                d.body,
                d.source_text,
                d.metadata_json,
                snippet(documents_fts, 1, '[', ']', ' ... ', 24) AS snippet,
                bm25(documents_fts) AS score
            FROM documents_fts
            JOIN documents d ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (query, limit),
        )
        return self._rows_to_dicts(result)

    def get_document(self, document_id: int) -> dict[str, Any] | None:
        """
        Return one full document by primary key.
        """
        result = self.conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        row = result.fetchone()
        return dict(row) if row else None

    def list_transactions(self, document_id: int | None = None) -> list[dict[str, Any]]:
        """
        Return parsed transaction rows extracted from transaction-like text files.
        """
        if document_id is None:
            result = self.conn.execute(
                "SELECT * FROM transactions ORDER BY document_id, line_no"
            )
        else:
            result = self.conn.execute(
                "SELECT * FROM transactions WHERE document_id = ? ORDER BY line_no",
                (document_id,),
            )
        return self._rows_to_dicts(result)

    # ── Utils ─────────────────────────────────────────────────────────────────

    def query(self, sql: str) -> list[dict[str, Any]]:
        """
        Execute arbitrary SQL and return rows as dictionaries.
        """
        result = self.conn.execute(sql)
        return self._rows_to_dicts(result)

    def query_params(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        """
        Execute parameterized SQL and return rows as dictionaries.
        """
        result = self.conn.execute(sql, params)
        return self._rows_to_dicts(result)

    def tables(self) -> list[str]:
        """
        Return the list of all user tables and virtual tables.
        """
        result = self.conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        return [row[0] for row in result.fetchall()]

    def schema(self, table_name: str) -> list[dict[str, Any]]:
        """
        Return column metadata for a given table.
        """
        result = self.conn.execute(f"PRAGMA table_info({table_name})")
        return self._rows_to_dicts(result)

    def close(self) -> None:
        """
        Close the SQLite connection.
        """
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _iter_supported_files(self, directory: Path) -> Iterable[Path]:
        """
        Yield supported files in deterministic sorted order.
        """
        for path in sorted(directory.rglob('*')):
            if path.is_file() and path.suffix.lower() in {'.md', '.txt', '.json'}:
                yield path

    def _upsert_document(self, path: Path) -> int:
        """
        Insert or update one document and rebuild derived transaction rows if needed.
        """
        parsed = self._parse_document(path)

        self.conn.execute(
            """
            INSERT INTO documents(
                path, filename, doc_type, title, body, source_text,
                metadata_json, file_size, modified_ts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                filename=excluded.filename,
                doc_type=excluded.doc_type,
                title=excluded.title,
                body=excluded.body,
                source_text=excluded.source_text,
                metadata_json=excluded.metadata_json,
                file_size=excluded.file_size,
                modified_ts=excluded.modified_ts,
                indexed_at=CURRENT_TIMESTAMP
            """,
            (
                parsed.path,
                parsed.filename,
                parsed.doc_type,
                parsed.title,
                parsed.body,
                parsed.source_text,
                parsed.metadata_json,
                parsed.file_size,
                parsed.modified_ts,
            ),
        )

        document_id = self.conn.execute(
            "SELECT id FROM documents WHERE path = ?",
            (parsed.path,),
        ).fetchone()[0]

        if parsed.doc_type == 'transactions':
            self._rebuild_transactions(document_id, parsed.source_text)
        else:
            self.conn.execute("DELETE FROM transactions WHERE document_id = ?", (document_id,))

        return int(document_id)

    def _parse_document(self, path: Path) -> ParsedDocument:
        """
        Convert one file into a normalized document model.

        Markdown keeps its text body and derives title from the first H1.
        JSON is flattened into searchable text while preserving raw content.
        Text files use the filename as the title.
        """
        raw_text = path.read_text(encoding='utf-8')
        source_text = self._normalize_text(raw_text)
        doc_type = self._detect_doc_type(path)
        stat = path.stat()

        metadata = {
            'filename': path.name,
            'suffix': path.suffix.lower(),
            'doc_type': doc_type,
        }

        if path.suffix.lower() == '.md':
            title = self._extract_markdown_title(source_text, path.name)
            body = source_text
        elif path.suffix.lower() == '.json':
            parsed = json.loads(raw_text)
            body = '\n'.join(self._flatten_json(parsed))
            title = path.stem
            metadata['json_top_level_type'] = type(parsed).__name__
        else:
            title = path.name
            body = source_text

        return ParsedDocument(
            path=str(path.resolve()),
            filename=path.name,
            doc_type=doc_type,
            title=title,
            body=body,
            source_text=source_text,
            metadata_json=json.dumps(metadata, ensure_ascii=False),
            file_size=stat.st_size,
            modified_ts=stat.st_mtime,
        )

    def _rebuild_transactions(self, document_id: int, source_text: str) -> None:
        """
        Rebuild structured transaction rows from lines like 'A -> item -> B'.
        """
        self.conn.execute("DELETE FROM transactions WHERE document_id = ?", (document_id,))
        for line_no, line in enumerate(source_text.splitlines(), start=1):
            clean = line.strip()
            if not clean or '->' not in clean:
                continue

            parts = [part.strip() for part in clean.split('->')]
            if len(parts) != 3:
                continue

            self.conn.execute(
                """
                INSERT INTO transactions(document_id, line_no, from_city, item, to_city, raw_line)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (document_id, line_no, parts[0], parts[1], parts[2], clean),
            )

    def _detect_doc_type(self, path: Path) -> str:
        """
        Infer logical document type from filename and extension.
        """

        name = path.name.lower()
        if 'readme' in name:
            return 'readme'
        if 'rozmow' in name:
            return 'notes'
        if 'ogloszen' in name or 'ogłoszen' in name:
            return 'announcements'
        if 'transakc' in name:
            return 'transactions'
        if path.suffix.lower() == '.md':
            return 'markdown'
        if path.suffix.lower() == '.json':
            return 'json'
        return 'text'


    def _extract_markdown_title(self, text: str, fallback: str) -> str:
        """
        Return the first Markdown H1 heading or a fallback filename.
        """
        for line in text.splitlines():
            if line.startswith('# '):
                return line[2:].strip()
        return fallback

    def _normalize_text(self, text: str) -> str:
        """
        Normalize line endings and trim trailing spaces.
        """
        lines = [line.rstrip() for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
        return '\n'.join(lines).strip()

    def _flatten_json(self, value: Any, prefix: str = '') -> list[str]:
        """
        Flatten nested JSON into readable searchable text lines.
        """
        parts: list[str] = []
        if isinstance(value, dict):
            for key, val in value.items():
                next_prefix = f"{prefix}.{key}" if prefix else str(key)
                parts.append(next_prefix)
                parts.extend(self._flatten_json(val, next_prefix))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                next_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
                parts.extend(self._flatten_json(item, next_prefix))
        else:
            if prefix:
                parts.append(f"{prefix}: {value}")
            else:
                parts.append(str(value))
        return parts

    def _rows_to_dicts(self, result: sqlite3.Cursor) -> list[dict[str, Any]]:
        """
        Convert sqlite3 rows into plain dictionaries.
        """
        return [dict(row) for row in result.fetchall()]

    def _count(self, table_name: str) -> int:
        """
        Return row count for a table.
        """
        return self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

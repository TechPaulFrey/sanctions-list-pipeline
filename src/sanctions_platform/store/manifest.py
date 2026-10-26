from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

import duckdb

DDL = """
CREATE TABLE IF NOT EXISTS raw_manifest (
    run_id VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    url VARCHAR NOT NULL,
    fetched_at_utc TIMESTAMP NOT NULL,
    http_status INTEGER,
    etag VARCHAR,
    last_modified VARCHAR,
    bytes BIGINT,
    sha256 VARCHAR,
    outcome VARCHAR NOT NULL CHECK (outcome IN ('stored', 'unchanged', 'failed')),
    error_message VARCHAR,
    raw_path VARCHAR,
    content_sha256 VARCHAR
)
"""

# Upgrades manifests created before content_sha256 existed (decision 0002).
MIGRATIONS = ("ALTER TABLE raw_manifest ADD COLUMN IF NOT EXISTS content_sha256 VARCHAR",)


@dataclass
class ManifestRow:
    run_id: str
    source: str
    url: str
    fetched_at_utc: datetime
    outcome: str = "failed"
    http_status: int | None = None
    etag: str | None = None
    last_modified: str | None = None
    bytes: int | None = None
    sha256: str | None = None
    error_message: str | None = None
    raw_path: str | None = None
    content_sha256: str | None = None


_COLUMNS = [f.name for f in fields(ManifestRow)]


class Manifest:
    def __init__(self, con: duckdb.DuckDBPyConnection):
        self.con = con
        con.execute(DDL)
        for statement in MIGRATIONS:
            con.execute(statement)

    @classmethod
    def open(cls, path: Path) -> "Manifest":
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(duckdb.connect(str(path)))

    def record(self, row: ManifestRow) -> None:
        values = asdict(row)
        self.con.execute(
            f"INSERT INTO raw_manifest ({', '.join(_COLUMNS)}) "
            f"VALUES ({', '.join('?' for _ in _COLUMNS)})",
            [values[c] for c in _COLUMNS],
        )

    def last_success(self, source: str, url: str) -> ManifestRow | None:
        """Latest stored or unchanged row; both carry the hash and path of the current file."""
        result = self.con.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM raw_manifest "
            "WHERE source = ? AND url = ? AND outcome <> 'failed' "
            "ORDER BY fetched_at_utc DESC LIMIT 1",
            [source, url],
        ).fetchone()
        return ManifestRow(**dict(zip(_COLUMNS, result))) if result else None

    def rows_for_run(self, run_id: str) -> list[ManifestRow]:
        result = self.con.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM raw_manifest WHERE run_id = ? "
            "ORDER BY fetched_at_utc",
            [run_id],
        ).fetchall()
        return [ManifestRow(**dict(zip(_COLUMNS, r))) for r in result]

    def close(self) -> None:
        self.con.close()

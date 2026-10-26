import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path

from sanctions_platform.config import VOLATILE_PATTERNS


def content_sha256(source: str, path: Path, sha256: str) -> str:
    """Hash used for change detection: the file hash, unless the source has volatile bytes."""
    patterns = VOLATILE_PATTERNS.get(source)
    if not patterns:
        return sha256
    data = path.read_bytes()
    for pattern in patterns:
        data = re.sub(pattern, b"", data)
    return hashlib.sha256(data).hexdigest()


def raw_relpath(
    source: str, fetched_at: datetime, sha256: str, ext: str, label: str | None = None
) -> Path:
    """Path relative to the data directory, so lineage survives moving between machines."""
    stamp = fetched_at.strftime("%Y%m%dT%H%M%SZ")
    name = f"{stamp}_{label}_{sha256[:12]}.{ext}" if label else f"{stamp}_{sha256[:12]}.{ext}"
    return (
        Path("raw") / source / f"{fetched_at:%Y}" / f"{fetched_at:%m}" / f"{fetched_at:%d}" / name
    )


def temp_path(data_dir: Path, source: str) -> Path:
    return data_dir / "raw" / source / ".tmp" / f"{uuid.uuid4().hex}.part"


def promote(tmp: Path, final: Path) -> None:
    """Move a finished download into place. Never overwrites an existing raw file."""
    final.parent.mkdir(parents=True, exist_ok=True)
    if final.exists():
        # Same source, second and hash means identical bytes; keep the original.
        tmp.unlink()
    else:
        tmp.rename(final)

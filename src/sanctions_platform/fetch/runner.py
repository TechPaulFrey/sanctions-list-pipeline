import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.lexbor import LexborHTMLParser
from tenacity.wait import wait_base

from sanctions_platform.config import (
    FILE_SOURCES,
    NIGSAC_BASE_URL,
    NIGSAC_DELAY_SECONDS,
    NIGSAC_LIST_URL,
    NIGSAC_ROBOTS_URL,
    USER_AGENT,
)
from sanctions_platform.fetch import http
from sanctions_platform.store.manifest import Manifest, ManifestRow
from sanctions_platform.store.raw import content_sha256, promote, raw_relpath, temp_path

_DETAIL_HREF = re.compile(r"/(IndSancDetails|EntSancDetails)\?id=(\d+)", re.IGNORECASE)
_DETAIL_LABEL = {"indsancdetails": "ind", "entsancdetails": "ent"}


def _utcnow() -> datetime:
    # Naive UTC, matching the TIMESTAMP column in raw_manifest.
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


@dataclass
class FetchContext:
    client: httpx.Client
    manifest: Manifest
    data_dir: Path
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    wait: wait_base = http.DEFAULT_WAIT
    sleep: Callable[[float], None] = time.sleep
    now: Callable[[], datetime] = _utcnow


def _error_status(exc: Exception) -> int | None:
    if isinstance(exc, http.RetryableStatusError):
        return exc.status_code
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return None


def record_failure(ctx: FetchContext, source: str, url: str, message: str) -> ManifestRow:
    row = ManifestRow(ctx.run_id, source, url, ctx.now(), error_message=message)
    ctx.manifest.record(row)
    return row


def fetch_to_store(
    ctx: FetchContext, source: str, url: str, ext: str, label: str | None = None
) -> ManifestRow:
    """Download one URL into the raw store and record the attempt, whatever happens."""
    row = ManifestRow(ctx.run_id, source, url, ctx.now())
    prev = ctx.manifest.last_success(source, url)
    tmp = temp_path(ctx.data_dir, source)
    try:
        dl = http.download(
            ctx.client,
            url,
            tmp,
            etag=prev.etag if prev else None,
            last_modified=prev.last_modified if prev else None,
            wait=ctx.wait,
        )
        row.http_status = dl.status
        if dl.status == 304 and prev:
            row.outcome = "unchanged"
            row.etag = dl.etag or prev.etag
            row.last_modified = dl.last_modified or prev.last_modified
            row.sha256, row.bytes, row.raw_path = prev.sha256, prev.bytes, prev.raw_path
            row.content_sha256 = prev.content_sha256 or prev.sha256
        else:
            row.etag, row.last_modified = dl.etag, dl.last_modified
            row.sha256, row.bytes = dl.sha256, dl.bytes
            row.content_sha256 = content_sha256(source, tmp, dl.sha256)
            if prev and (prev.content_sha256 or prev.sha256) == row.content_sha256:
                tmp.unlink()
                row.outcome = "unchanged"
                row.raw_path = prev.raw_path
            else:
                rel = raw_relpath(source, row.fetched_at_utc, dl.sha256, ext, label)
                promote(tmp, ctx.data_dir / rel)
                row.outcome = "stored"
                row.raw_path = rel.as_posix()
    except Exception as exc:  # noqa: BLE001 - any failure becomes a manifest row, never a crash
        tmp.unlink(missing_ok=True)
        row.outcome = "failed"
        row.http_status = _error_status(exc) or row.http_status
        row.error_message = f"{type(exc).__name__}: {exc}"
    ctx.manifest.record(row)
    return row


def extract_detail_links(html: str) -> list[tuple[str, str]]:
    """Return (label, absolute url) for every NIGSAC detail link, in page order."""
    seen: dict[str, str] = {}
    for node in LexborHTMLParser(html).css("a[href]"):
        match = _DETAIL_HREF.search(node.attributes.get("href") or "")
        if not match:
            continue
        page, detail_id = match.groups()
        label = f"{_DETAIL_LABEL[page.lower()]}-{detail_id}"
        seen.setdefault(label, f"{NIGSAC_BASE_URL}/{page}?id={detail_id}")
    return list(seen.items())


def load_robots(ctx: FetchContext) -> RobotFileParser:
    """A 4xx robots.txt means no rules (RFC 9309); any other failure raises."""
    response = http.get(ctx.client, NIGSAC_ROBOTS_URL, wait=ctx.wait)
    parser = RobotFileParser()
    if response.status_code == 200:
        parser.parse(response.text.splitlines())
    elif 400 <= response.status_code < 500:
        parser.allow_all = True
    else:
        raise RuntimeError(f"robots.txt returned HTTP {response.status_code}")
    return parser


def fetch_nigsac(ctx: FetchContext) -> list[ManifestRow]:
    try:
        robots = load_robots(ctx)
    except Exception as exc:  # noqa: BLE001 - without robots.txt we do not crawl at all
        message = f"robots.txt unavailable, not crawling: {type(exc).__name__}: {exc}"
        return [record_failure(ctx, "nigsac_list", NIGSAC_LIST_URL, message)]

    if not robots.can_fetch(USER_AGENT, NIGSAC_LIST_URL):
        return [record_failure(ctx, "nigsac_list", NIGSAC_LIST_URL, "disallowed by robots.txt")]

    ctx.sleep(NIGSAC_DELAY_SECONDS)
    list_row = fetch_to_store(ctx, "nigsac_list", NIGSAC_LIST_URL, "html")
    rows = [list_row]
    if list_row.outcome == "failed":
        return rows

    html = (ctx.data_dir / list_row.raw_path).read_text(encoding="utf-8")
    for label, url in extract_detail_links(html):
        if not robots.can_fetch(USER_AGENT, url):
            rows.append(record_failure(ctx, "nigsac_detail", url, "disallowed by robots.txt"))
            continue
        ctx.sleep(NIGSAC_DELAY_SECONDS)
        rows.append(fetch_to_store(ctx, "nigsac_detail", url, "html", label=label))
    return rows


def run_all(ctx: FetchContext) -> list[ManifestRow]:
    rows = [fetch_to_store(ctx, s.name, s.url, s.ext) for s in FILE_SOURCES]
    rows.extend(fetch_nigsac(ctx))
    return rows

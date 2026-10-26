import hashlib
from dataclasses import dataclass
from pathlib import Path

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential
from tenacity.wait import wait_base

from sanctions_platform.config import TIMEOUT_SECONDS, USER_AGENT

DEFAULT_WAIT = wait_exponential(multiplier=2, min=2, max=30)
MAX_ATTEMPTS = 3


class RetryableStatusError(Exception):
    """Raised for HTTP 429 and 5xx so tenacity retries them."""

    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


@dataclass
class Download:
    status: int
    etag: str | None
    last_modified: str | None
    sha256: str | None = None
    bytes: int | None = None


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def _retrying(wait: wait_base) -> Retrying:
    return Retrying(
        stop=stop_after_attempt(MAX_ATTEMPTS),
        wait=wait,
        retry=retry_if_exception_type((httpx.TransportError, RetryableStatusError)),
        reraise=True,
    )


def _raise_if_retryable(status_code: int) -> None:
    if status_code == 429 or status_code >= 500:
        raise RetryableStatusError(status_code)


def get(client: httpx.Client, url: str, wait: wait_base = DEFAULT_WAIT) -> httpx.Response:
    """Small in-memory GET with retries. Returns 4xx responses for the caller to judge."""
    for attempt in _retrying(wait):
        with attempt:
            response = client.get(url)
            _raise_if_retryable(response.status_code)
            return response
    raise AssertionError("unreachable")


def download(
    client: httpx.Client,
    url: str,
    dest: Path,
    etag: str | None = None,
    last_modified: str | None = None,
    wait: wait_base = DEFAULT_WAIT,
) -> Download:
    """Stream url to dest, hashing as it goes. A 304 leaves dest untouched."""
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    for attempt in _retrying(wait):
        with attempt, client.stream("GET", url, headers=headers) as response:
            _raise_if_retryable(response.status_code)
            result = Download(
                status=response.status_code,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )
            if response.status_code == 304:
                return result
            response.raise_for_status()
            digest = hashlib.sha256()
            size = 0
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            result.sha256 = digest.hexdigest()
            result.bytes = size
            return result
    raise AssertionError("unreachable")

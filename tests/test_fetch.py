from datetime import datetime, timedelta

import duckdb
import httpx
import pytest
import respx
from tenacity import wait_none

from sanctions_platform.config import (
    FILE_SOURCES,
    NIGSAC_LIST_URL,
    NIGSAC_ROBOTS_URL,
)
from sanctions_platform.fetch.http import make_client
from sanctions_platform.fetch.runner import (
    FetchContext,
    extract_detail_links,
    fetch_nigsac,
    fetch_to_store,
    run_all,
)
from sanctions_platform.store.manifest import Manifest

LIST_HTML = """
<table><tr><td>A</td><td><a class="btn" href="/IndSancDetails?id=1036">Details</a></td></tr>
<tr><td>B</td><td><a href="/IndSancDetails?id=1036">dup</a></td></tr></table>
<table><tr><td>C</td><td><a href="/EntSancDetails?id=2">Details</a></td></tr></table>
<a href="/Sanctions">not a detail link</a>
"""
DETAIL_IND = "https://nigsac.gov.ng/IndSancDetails?id=1036"
DETAIL_ENT = "https://nigsac.gov.ng/EntSancDetails?id=2"
UN = next(s for s in FILE_SOURCES if s.name == "un")


class Clock:
    """Advances one minute per call so each fetch gets a distinct timestamp."""

    def __init__(self):
        self.t = datetime(2026, 10, 26, 6, 0, 0)

    def __call__(self):
        self.t += timedelta(minutes=1)
        return self.t


@pytest.fixture
def ctx(tmp_path):
    manifest = Manifest(duckdb.connect(":memory:"))
    with make_client() as client:
        yield FetchContext(
            client=client,
            manifest=manifest,
            data_dir=tmp_path,
            wait=wait_none(),
            sleep=lambda _seconds: None,
            now=Clock(),
        )
    manifest.close()


def mock_all_sources(router, nigsac_robots_status=404):
    for source in FILE_SOURCES:
        router.get(source.url).respond(200, content=f"<{source.name}/>".encode())
    router.get(NIGSAC_ROBOTS_URL).respond(nigsac_robots_status, text="")
    router.get(NIGSAC_LIST_URL).respond(200, text=LIST_HTML)
    router.get(DETAIL_IND).respond(200, text="<html>ind</html>")
    router.get(DETAIL_ENT).respond(200, text="<html>ent</html>")


def outcomes(rows):
    return {(r.source, r.url): r.outcome for r in rows}


def test_first_run_stores_second_run_unchanged(ctx):
    with respx.mock(assert_all_called=False) as router:
        mock_all_sources(router)
        first = run_all(ctx)
        second = run_all(ctx)

    assert {o for o in outcomes(first).values()} == {"stored"}
    assert {o for o in outcomes(second).values()} == {"unchanged"}
    assert len(first) == len(FILE_SOURCES) + 3  # list page plus two unique detail pages
    for row in first:
        assert (ctx.data_dir / row.raw_path).read_bytes()
    stored_files = [p for p in ctx.data_dir.rglob("*") if p.is_file()]
    assert len(stored_files) == len(first)  # second run left no extra or temporary files


def test_raw_path_layout(ctx):
    with respx.mock(assert_all_called=False) as router:
        mock_all_sources(router)
        rows = fetch_nigsac(ctx)

    detail = next(r for r in rows if r.url == DETAIL_IND)
    parts = detail.raw_path.split("/")
    assert parts[:5] == ["raw", "nigsac_detail", "2026", "10", "26"]
    assert parts[5].startswith("20261026T06")
    assert f"_ind-1036_{detail.sha256[:12]}.html" in parts[5]


def test_conditional_request_304_records_unchanged(ctx):
    with respx.mock as router:
        route = router.get(UN.url)
        route.side_effect = [
            httpx.Response(200, content=b"<un/>", headers={"ETag": '"v1"'}),
            httpx.Response(304),
        ]
        first = fetch_to_store(ctx, UN.name, UN.url, UN.ext)
        second = fetch_to_store(ctx, UN.name, UN.url, UN.ext)

    assert route.calls[1].request.headers["If-None-Match"] == '"v1"'
    assert first.outcome == "stored"
    assert second.outcome == "unchanged"
    assert second.http_status == 304
    assert second.sha256 == first.sha256
    assert second.raw_path == first.raw_path


def test_changed_content_is_stored_again(ctx):
    with respx.mock as router:
        router.get(UN.url).side_effect = [
            httpx.Response(200, content=b"<un>1</un>"),
            httpx.Response(200, content=b"<un>2</un>"),
        ]
        first = fetch_to_store(ctx, UN.name, UN.url, UN.ext)
        second = fetch_to_store(ctx, UN.name, UN.url, UN.ext)

    assert (first.outcome, second.outcome) == ("stored", "stored")
    assert first.raw_path != second.raw_path


def test_http_503_records_failure_and_other_sources_continue(ctx):
    with respx.mock(assert_all_called=False) as router:
        mock_all_sources(router)
        failing = router.get(UN.url).respond(503)
        rows = run_all(ctx)

    un_row = next(r for r in rows if r.source == "un")
    assert un_row.outcome == "failed"
    assert un_row.http_status == 503
    assert "503" in un_row.error_message
    assert failing.call_count == 3  # retried before giving up
    assert all(r.outcome == "stored" for r in rows if r.source != "un")
    assert ctx.manifest.rows_for_run(ctx.run_id)[0].outcome == "failed"
    assert not list(ctx.data_dir.rglob("*.part"))


def test_connection_error_records_failure(ctx):
    with respx.mock as router:
        router.get(UN.url).mock(side_effect=httpx.ConnectError("refused"))
        row = fetch_to_store(ctx, UN.name, UN.url, UN.ext)

    assert row.outcome == "failed"
    assert row.http_status is None
    assert "ConnectError" in row.error_message


def test_client_error_is_not_retried(ctx):
    with respx.mock as router:
        route = router.get(UN.url).respond(404)
        row = fetch_to_store(ctx, UN.name, UN.url, UN.ext)

    assert row.outcome == "failed"
    assert row.http_status == 404
    assert route.call_count == 1


def test_nigsac_sleeps_between_requests(ctx):
    sleeps = []
    ctx.sleep = sleeps.append
    with respx.mock(assert_all_called=False) as router:
        mock_all_sources(router)
        rows = fetch_nigsac(ctx)

    assert len(rows) == 3
    assert sleeps == [2.0, 2.0, 2.0]


def test_nigsac_robots_disallow_stops_crawl(ctx):
    with respx.mock(assert_all_called=False) as router:
        mock_all_sources(router, nigsac_robots_status=200)
        router.get(NIGSAC_ROBOTS_URL).respond(200, text="User-agent: *\nDisallow: /\n")
        list_route = router.get(NIGSAC_LIST_URL)
        rows = fetch_nigsac(ctx)

    assert [(r.source, r.outcome, r.error_message) for r in rows] == [
        ("nigsac_list", "failed", "disallowed by robots.txt")
    ]
    assert not list_route.called


def test_nigsac_robots_server_error_stops_crawl(ctx):
    with respx.mock(assert_all_called=False) as router:
        mock_all_sources(router)
        router.get(NIGSAC_ROBOTS_URL).respond(500)
        rows = fetch_nigsac(ctx)

    assert len(rows) == 1
    assert rows[0].outcome == "failed"
    assert "robots.txt unavailable" in rows[0].error_message


def test_nigsac_list_failure_skips_details(ctx):
    with respx.mock(assert_all_called=False) as router:
        mock_all_sources(router)
        router.get(NIGSAC_LIST_URL).respond(503)
        detail_route = router.get(DETAIL_IND)
        rows = fetch_nigsac(ctx)

    assert [r.outcome for r in rows] == ["failed"]
    assert not detail_route.called


def _list_page(clock: str, body: str) -> str:
    return f'<label class="tabs__label"> LIST <span>{clock}</span></label>{body}'


def test_nigsac_list_clock_alone_is_not_a_change(ctx):
    with respx.mock as router:
        router.get(NIGSAC_LIST_URL).side_effect = [
            httpx.Response(200, text=_list_page("10/26/2026 3:27:57 PM", "<td>A</td>")),
            httpx.Response(200, text=_list_page("10/26/2026 3:30:46 PM", "<td>A</td>")),
            httpx.Response(200, text=_list_page("10/27/2026 7:00:02 AM", "<td>B</td>")),
        ]
        rows = [fetch_to_store(ctx, "nigsac_list", NIGSAC_LIST_URL, "html") for _ in range(3)]

    assert [r.outcome for r in rows] == ["stored", "unchanged", "stored"]
    assert rows[0].sha256 != rows[1].sha256  # raw bytes differ and are hashed as received
    assert rows[0].content_sha256 == rows[1].content_sha256


def test_extract_detail_links_dedupes_and_labels():
    assert extract_detail_links(LIST_HTML) == [
        ("ind-1036", DETAIL_IND),
        ("ent-2", DETAIL_ENT),
    ]

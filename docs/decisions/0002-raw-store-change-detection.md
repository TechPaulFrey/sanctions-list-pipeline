# 0002. Raw store keys and change detection

Date: 26 October 2026
Status: accepted

## Context

The fetch layer stores a raw file only when it differs from the last stored version. Two facts from the first live runs shaped how "differs" is decided:

1. NIGSAC is one list page plus 69 detail pages under one source, not one file.
2. The NIGSAC list page prints the server clock (`10/26/2026 3:27:57 PM`) in its tab labels, so its bytes change on every request even when the list has not changed. In the first two consecutive runs it was stored twice while every other file was unchanged.

## Decision

* Change detection is keyed on `(source, url)`, not on source alone, so each NIGSAC detail page is compared with its own previous version. NIGSAC uses two manifest sources: `nigsac_list` and `nigsac_detail`. The UK formats are `uk_xml` and `uk_csv`.
* Detail files carry a label in the file name (`<fetched_at>_ind-1036_<hash12>.html`) so a file can be traced to its page without opening the manifest. Paths otherwise follow BUILD_LOG section 4.
* `raw_path` is stored relative to the data directory (`raw/un/2026/10/26/...`), so lineage works on a laptop and in GitHub Actions.
* The manifest gains a column, `content_sha256`. It equals `sha256` except for sources listed in `VOLATILE_PATTERNS` in `config.py`, where it is the hash of the file with those patterns removed. Change detection compares `content_sha256`. `sha256` remains the hash of the exact bytes stored.
* Raw files are never altered. Normalisation only affects the hash used for the comparison.
* Conditional requests (`If-None-Match`, `If-Modified-Since`) are sent when the server provided an ETag or Last-Modified header. UN, OFAC and UK support them and answer 304, which avoids downloading about 100 MB a day. NIGSAC does not, so it relies on hashing.

## Consequences

* A volatile pattern that is too broad could hide a real change. The single pattern matches only a `<span>` containing nothing but a US-format timestamp. A test proves that a page with a changed body and a changed clock is stored.
* The two duplicate list pages stored before this fix stay in the raw store, because raw files are never deleted by code.
* Existing manifests are upgraded in place with `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. Rows written before the change have a null `content_sha256`, and comparison falls back to `sha256`.
* The history persistence record planned in BUILD_LOG Phase 8 becomes 0003.

# UN Security Council Consolidated List

Verified: 26 October 2026

| | |
|---|---|
| Manifest source | `un` |
| URL | https://scsanctions.un.org/resources/xml/en/consolidated.xml |
| Format | XML, root `CONSOLIDATED_LIST`, no namespace, `xsi:noNamespaceSchemaLocation="https://www.un.org/sc/resources/sc-sanctions.xsd"` |
| Observed size | 2,175,904 bytes; 733 `INDIVIDUAL` and 274 `ENTITY` records |
| Conditional requests | Server sends `ETag` and `Last-Modified` and answers 304 to a conditional GET |
| Licence | Unresolved. See [data_licences.md](../data_licences.md) |

## Structure

`CONSOLIDATED_LIST` (attribute `dateGenerated`) holds `INDIVIDUALS/INDIVIDUAL` and `ENTITIES/ENTITY`. Each record carries `DATAID`, `VERSIONNUM`, name parts (`FIRST_NAME`, `SECOND_NAME`, ...) and a UN reference number such as `QDi.322` or `QDe.138`. The parser is written in Phase 2.

## Cadence

The plan says the list is regenerated nightly. On 26 October 2026 at 14:27 UTC the file had `dateGenerated="2026-10-24T23:00:07.335Z"` and `Last-Modified: Sat, 24 Oct 2026 23:01:18 GMT`, so it had not been regenerated for about 39 hours. The daily manifest will show the real cadence. Check this before setting the 36-hour freshness warning in Phase 3.

## Quirks

* None observed at the fetch layer yet.

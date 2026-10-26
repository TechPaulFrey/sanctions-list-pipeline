# Nigeria Sanctions List (NIGSAC)

Verified: 26 October 2026

| | |
|---|---|
| Manifest sources | `nigsac_list` (list page), `nigsac_detail` (one row per detail page) |
| List page | https://nigsac.gov.ng/IndSancList |
| Detail pages | `https://nigsac.gov.ng/IndSancDetails?id=<n>` (individuals and groups), `https://nigsac.gov.ng/EntSancDetails?id=<n>` (entities) |
| robots.txt | https://nigsac.gov.ng/robots.txt returns 404. Under RFC 9309 that means no crawl restrictions. The fetcher checks it on every run and stops if it ever returns rules that disallow us or a server error. |
| Format | Server-rendered HTML, `text/html; charset=utf-8`. No CSV, XML or API. |
| Observed size | List page 104,656 bytes, two tables, 54 `IndSancDetails` and 15 `EntSancDetails` links. Detail pages up to 44,029 bytes. |
| Conditional requests | No `ETag` or `Last-Modified`; change detection is by content hash. |
| Licence | Site footer states all rights reserved. See [data_licences.md](../data_licences.md) and BUILD_LOG section 10. |

## Fetch behaviour

Fetch robots.txt, then the list page, then every detail page linked from it, with a 2-second pause before each request. A full crawl takes about three minutes. Detail links are relative (`/IndSancDetails?id=1040`) and turned into absolute URLs. Each detail file name carries a label such as `ind-1036` or `ent-2`.

## Volatile content

The list page prints the server's current time in both tab labels, for example `<span>10/26/2026 3:27:57 PM</span>`. Every download therefore differs byte for byte. The raw file is stored unaltered, and `content_sha256` in the manifest blanks that span before hashing, so change detection ignores it. See decision 0002. The clock read 3:27 PM when the request was made at 14:27 UTC, which confirms the site runs on West Africa Time (UTC+1). This supports the Phase 2 timezone assumption.

Detail pages showed no volatile content: all 69 were unchanged across consecutive runs.

## Detail page fields

Fields appear as `<dt>` labels. Values are not reproduced here because they include personal data.

* All 69 pages: Record Date, Sanction Date, Reason for Designation, Comments, Address, Aliases, Press Release, Narrative Summary.
* 54 individual and group pages: First Name, MiddleName, Surname, Date of Birth, Birth Country, Birth City, Phone Number, Nationality.
* 15 entity pages: Referance Number (misspelled in the source), Entity Name, Incorporation Number, Incorporation Date, Phone Numbers.

Entity detail pages do carry a reference number, even though the entity table on the list page has no reference column (BUILD_LOG section 3, issue 9).

## Privacy

Detail pages contain phone numbers, addresses and passport numbers. Raw files stay in the git-ignored `data/` folder and never enter the repository. Staging rules are in BUILD_LOG section 10.

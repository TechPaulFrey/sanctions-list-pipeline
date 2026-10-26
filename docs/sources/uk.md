# UK Sanctions List (FCDO)

Verified: 26 October 2026

| | XML (`uk_xml`) | CSV (`uk_csv`) |
|---|---|---|
| URL | https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml | https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv |
| Observed size | 22,096,429 bytes | 50,185,226 bytes |
| Records | 6,423 `Designation` elements | 58,645 data rows; 6,423 distinct `Unique ID` |
| Generated | `DateGenerated` 26/10/2026 | First line `Report Date: 26-Oct-2026` |
| Conditional requests | 304 supported | 304 supported |

Schema (version 4.33.3): https://assets.publishing.service.gov.uk/media/6916e72cdb01ecfcf96fc96b/SanctionsListSchema-4.33.3.xsd (16,418 bytes, `Last-Modified` 14 November 2025). Validation against it is part of Phase 2.

Licence: Open Government Licence v3.0. Credit line: "Contains public sector information licensed under the Open Government Licence v3.0."

## Structure

XML root `Designations` holds `DateGenerated` and one `Designation` per party, with `LastUpdated`, `DateDesignated`, `UniqueID`, `OFSIGroupID`, `UNReferenceNumber`, `Names/Name` (`Name1` to `Name6`, `NameType`) and more.

The CSV has one row per name or alias, not one per designation, and its first line is a `Report Date` banner above the header row. Designation types seen: Entity, Individual, Ship.

## Format reconciliation

On 26 October 2026 both formats held exactly the same set of 6,423 Unique IDs. The Phase 4 check must compare distinct Unique IDs, not row counts, because the CSV repeats a designation once per name.

## OFSI migration

5,136 of the 6,423 designations carry an `OFSI Group ID` (legacy, pre-28 January 2026). 997 carry a `UN Reference Number`, which is the deterministic link to the UN list in Phase 5.

## Quirks

* Dates are day-first (`29/06/2012`); OFAC's are month-first.
* The CSV is served as `application/octet-stream`, has no byte order mark, and starts with a banner line before the header.

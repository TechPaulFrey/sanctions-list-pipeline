# US OFAC Specially Designated Nationals (SDN) List

Verified: 26 October 2026

## SDN.XML (manifest source `ofac`)

| | |
|---|---|
| URL | https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML |
| How the URL was found | The download page https://sanctionslist.ofac.treas.gov/Home/static/sdn.html lists SDN.XML but builds its links in JavaScript. The URL follows the same pattern as the documented SDN_ADVANCED.XML export and returned the file. |
| Format | XML, root `sdnList`, namespace `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML` |
| Observed size | 29,245,041 bytes; 19,471 `sdnEntry` elements, matching the file's own `Record_Count` |
| Publication | `Publish_Date` 10/21/2026 (US month-first format) |
| Conditional requests | `ETag` and `Last-Modified` sent; 304 returned on a conditional GET |

Structure: `publshInformation` (misspelled in the source) with `Publish_Date` and `Record_Count`, then one `sdnEntry` per party: `uid`, `lastName`, `firstName`, `sdnType`, `programList/program`, `akaList/aka` (with `type` and `category` of `strong` or `weak`), `addressList`, `idList`, `dateOfBirthList`, `nationalityList` and others.

The download page also lists SDN_ENHANCED.XML/ZIP, SDN_ADVANCED.XML/ZIP and SDN_XML.ZIP.

## Delta file (manifest source `ofac_delta`)

| | |
|---|---|
| URL | https://sanctionslistservice.ofac.treas.gov/changes/latest |
| Format | XML, root `sanctionsData`, namespace `https://www.treasury.gov/ofac/DeltaFile/1.0`, schema https://www.treasury.gov/ofac/downloads/sanctions/1.0/DeltaFile.xsd |
| Observed size | 103,434 bytes |
| Publication | `datePublished` 2026-10-21T00:00:00-04:00, `publicationType` "Standard Action". This is the same publication as the SDN.XML above. |

Structure, as observed:

* `publicationInfo`: `datePublished`, `publicationType`.
* `referenceValues`, `featureTypes`: empty in this file.
* `entities/entity`: one per changed party, with attributes `id` and `action`. Each entity is written in the advanced-format vocabulary: `generalInfo` (`identityId`, `entityType`), `sanctionsLists`, `sanctionsPrograms`, `sanctionsTypes`, `legalAuthorities`, `names` (with translations and name parts, including non-Latin scripts), `addresses` and more.

Observed actions in the 21 October 2026 file: `add` 18, `remove` 4. No other action values appeared. The XSD may allow others (for example updates), so check it before writing the Phase 4 reconciliation.

Key relationship, verified: the delta `entity/@id` equals the SDN.XML `sdnEntry/uid`. All 18 added ids are present in SDN.XML and none of the 4 removed ids are. This means Phase 4 can compare OFAC's reported adds and removes with our own change detection by uid.

## Licence

Unresolved. See [data_licences.md](../data_licences.md).

## Quirks

* The `publshInformation` element name is misspelled in the source; parse it as published.
* `Publish_Date` is month-first.

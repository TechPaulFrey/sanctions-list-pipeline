from dataclasses import dataclass
from pathlib import Path

USER_AGENT = (
    "sanctions-list-pipeline/0.1 (+https://github.com/TechPaulFrey/sanctions-list-pipeline)"
)
TIMEOUT_SECONDS = 60.0

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
WAREHOUSE_PATH = DATA_DIR / "warehouse" / "sanctions.duckdb"


@dataclass(frozen=True)
class FileSource:
    name: str
    url: str
    ext: str


# Single-file sources. URLs verified on 26 October 2026; see docs/sources/.
FILE_SOURCES = (
    FileSource("un", "https://scsanctions.un.org/resources/xml/en/consolidated.xml", "xml"),
    FileSource(
        "ofac",
        "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML",
        "xml",
    ),
    FileSource("ofac_delta", "https://sanctionslistservice.ofac.treas.gov/changes/latest", "xml"),
    FileSource("uk_xml", "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml", "xml"),
    FileSource("uk_csv", "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv", "csv"),
)

UK_XSD_URL = (
    "https://assets.publishing.service.gov.uk/media/6916e72cdb01ecfcf96fc96b/"
    "SanctionsListSchema-4.33.3.xsd"
)

NIGSAC_BASE_URL = "https://nigsac.gov.ng"
NIGSAC_ROBOTS_URL = f"{NIGSAC_BASE_URL}/robots.txt"
NIGSAC_LIST_URL = f"{NIGSAC_BASE_URL}/IndSancList"
# Politeness delay between NIGSAC requests; the site is small and government run.
NIGSAC_DELAY_SECONDS = 2.0

# Bytes that change on every request without the data changing. They are blanked only when
# computing content_sha256 for change detection; raw files are stored unaltered.
# The NIGSAC list page prints the server clock in its tab labels, e.g. "10/26/2026 3:27:57 PM".
VOLATILE_PATTERNS = {
    "nigsac_list": (rb"<span>\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2} [AP]M</span>",),
}

import sys
from collections import Counter

from sanctions_platform.config import DATA_DIR, WAREHOUSE_PATH
from sanctions_platform.fetch.http import make_client
from sanctions_platform.fetch.runner import FetchContext, run_all
from sanctions_platform.store.manifest import Manifest


def main() -> int:
    manifest = Manifest.open(WAREHOUSE_PATH)
    try:
        with make_client() as client:
            ctx = FetchContext(client=client, manifest=manifest, data_dir=DATA_DIR)
            rows = run_all(ctx)
    finally:
        manifest.close()

    by_source: dict[str, Counter] = {}
    for row in rows:
        by_source.setdefault(row.source, Counter())[row.outcome] += 1
    print(f"run_id {ctx.run_id}")
    for source, counts in by_source.items():
        print(f"{source:<14} " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for row in rows:
        if row.outcome == "failed":
            print(f"FAILED {row.source} {row.url}: {row.error_message}", file=sys.stderr)

    # Non-zero exit lets the scheduler flag a partial run without hiding the sources that worked.
    return 1 if any(r.outcome == "failed" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())

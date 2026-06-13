#!/usr/bin/env python3
"""Pre-fetch a dataset bag into the local cache.

Warms the local DerivaML cache for a (dataset_rid, version) without
running an execution. Useful when:

- You're about to start a training run and want the bag in cache so
  the actual `download_dataset_bag()` call inside the execution is
  near-instant.
- Your machine is about to go offline (travel, air-gapped review) and
  you want the bag local.
- You're running an experiment matrix where multiple executions will
  share the same input bag.

The cache key is `(dataset_rid, version, exclude_tables, materialize)`
plus the catalog's snapshot for that version, so re-running this
script with the same args after the first successful cache load is a
no-op.

This is a Python-only operation because the cache lives on the
caller's machine, not the MCP server's filesystem. There is no MCP
tool that warms a remote user's bag cache.
"""

from __future__ import annotations

import argparse
import sys

from deriva_ml import DerivaML
from deriva_ml.dataset.aux_classes import DatasetSpec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--dataset-rid", required=True,
                        help="The Dataset RID to warm into the cache.")
    parser.add_argument("--version", required=True,
                        help="Released version label (e.g. 1.0.0). Dev labels "
                             "(*.devN) cannot be cached — release the dataset first.")
    parser.add_argument("--metadata-only", action="store_true",
                        help="Cache table data only, skip asset file bytes "
                             "(materialize=False). Use for inspection.")
    parser.add_argument("--exclude-table", action="append", default=[],
                        help="Prune a table from the FK traversal. Repeatable.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the bag preview (row counts, asset sizes "
                             "per table) without downloading.")
    parser.add_argument("--cache-dir", default=None,
                        help="Local cache directory, if not the default "
                             "~/.deriva-ml. Pass the same value your DerivaML(...) "
                             "/ hydra default_deriva(...) config uses, or the bag "
                             "warms into the wrong (default) location.")
    args = parser.parse_args()

    # cache_dir is only passed when supplied, so the library applies its own
    # default when the user did not relocate the cache.
    kwargs = {"cache_dir": args.cache_dir} if args.cache_dir else {}
    ml = DerivaML(args.hostname, args.catalog_id, **kwargs)

    spec = DatasetSpec(
        rid=args.dataset_rid,
        version=args.version,
        exclude_tables=set(args.exclude_table) if args.exclude_table else None,
    )

    # Always preview first — cheap, no bytes transferred.
    info = ml.bag_info(spec)
    print(f"Bag preview for {args.dataset_rid} v{args.version}:")
    for table, stats in info.get("tables", {}).items():
        rows = stats.get("row_count", "?")
        size = stats.get("total_asset_size_mb", 0.0)
        print(f"  {table:40s} {rows:>8} rows, {size:>10.1f} MB assets")

    if args.dry_run:
        print("[DRY RUN] Skipping download.")
        return 0

    materialize = not args.metadata_only
    result = ml.cache_dataset(spec, materialize=materialize)
    print(f"Cached. {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Pre-fetch one or more dataset bags into the local cache.

Warms the local DerivaML cache for each (dataset_rid, version) without
running an execution. Useful when:

- You're about to start a training run and want the bag(s) in cache so
  the actual ``download_dataset_bag()`` call inside the execution is
  near-instant.
- Your machine is about to go offline (travel, air-gapped review) and
  you want the data local.
- You're running an experiment matrix where several executions share
  the same input bags.

The cache key is ``(dataset_rid, version, exclude_tables, materialize)``
plus the catalog's snapshot for that version, so re-running this script
with the same args after a successful cache load is a no-op.

Multiple datasets are warmed **sequentially**, not in parallel. Each
dataset's asset download is already concurrent inside the library
(``cache_dataset`` fetches asset files ~8-way by default), which
saturates a typical uplink on its own; launching several warms at once
would just split the same bandwidth and contend for it, not go faster.
Sequential keeps progress legible and lets one bad RID be isolated
without killing the rest.

This is a Python-only operation because the cache lives on the caller's
machine, not the MCP server's filesystem. There is no MCP tool that
warms a remote user's bag cache.

Progress: by default this enables the deriva-ml library's INFO logging,
which emits per-dataset "Materializing bag: N of M file(s) downloaded"
lines so a multi-GB warm isn't a silent wait. This is FILE-COUNT
progress, not bytes/percent (the library's fetch callback reports file
counts only). Pass ``--quiet`` to suppress it.

Example:
    # one dataset
    uv run python warm_cache.py --hostname dev.eye-ai.org --catalog-id 5 \\
        --dataset-rid 28CT --version 1.0.0

    # several at once (paired --dataset-rid / --version, in order)
    uv run python warm_cache.py --hostname dev.eye-ai.org --catalog-id 5 \\
        --dataset-rid 28CT --version 1.0.0 \\
        --dataset-rid 3WSE --version 2.1.0 \\
        --dataset-rid 9QPM --version 0.4.0
"""

from __future__ import annotations

import argparse
import logging
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--dataset-rid", action="append", required=True, dest="dataset_rids",
                        help="A Dataset RID to warm. Repeat for several datasets; "
                             "pair each with a --version in the same order.")
    parser.add_argument("--version", action="append", required=True, dest="versions",
                        help="Released version label (e.g. 1.0.0) for the "
                             "correspondingly-positioned --dataset-rid. Dev labels "
                             "(*.devN) cannot be cached — release the dataset first.")
    parser.add_argument("--metadata-only", action="store_true",
                        help="Cache table data only, skip asset file bytes "
                             "(materialize=False). Use for inspection.")
    parser.add_argument("--exclude-table", action="append", default=[],
                        help="Prune a table from the FK traversal (applied to "
                             "every dataset). Repeatable.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the bag preview (row counts, asset sizes "
                             "per table) for each dataset without downloading.")
    parser.add_argument("--cache-dir", default=None,
                        help="Local cache directory, if not the default "
                             "~/.deriva-ml. Pass the same value your DerivaML(...) "
                             "/ hydra default_deriva(...) config uses, or the bag "
                             "warms into the wrong (default) location.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress the per-dataset file-count progress lines "
                             "(the library's INFO logging). On by default.")
    args = parser.parse_args()

    if len(args.dataset_rids) != len(args.versions):
        parser.error(
            f"--dataset-rid given {len(args.dataset_rids)} time(s) but --version "
            f"given {len(args.versions)} time(s); they must be paired one-to-one "
            f"in the same order."
        )

    # Surface the library's file-count progress ("Materializing bag: N of M
    # file(s) downloaded") unless suppressed. This is the only progress the
    # library exposes — file counts, not bytes/percent.
    if not args.quiet:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        logging.getLogger("deriva_ml").setLevel(logging.INFO)

    # Imported here (not at module top) so --help and argument validation work
    # without deriva-ml installed, matching inspect_storage.py.
    from deriva_ml import DerivaML
    from deriva_ml.dataset.aux_classes import DatasetSpec

    kwargs = {"cache_dir": args.cache_dir} if args.cache_dir else {}
    ml = DerivaML(args.hostname, args.catalog_id, **kwargs)

    exclude = set(args.exclude_table) if args.exclude_table else None
    materialize = not args.metadata_only

    pairs = list(zip(args.dataset_rids, args.versions))
    failures: list[tuple[str, str, str]] = []  # (rid, version, error)

    for i, (rid, version) in enumerate(pairs, start=1):
        print(f"\n[{i}/{len(pairs)}] {rid} v{version}")
        spec = DatasetSpec(rid=rid, version=version, exclude_tables=exclude)

        # Preview first — cheap, no bytes transferred. Isolate per-dataset
        # failure (e.g. a deleted catalog, a dev-label version, a bad RID) so
        # one bad entry doesn't abort the rest of the batch.
        try:
            info = ml.bag_info(spec)
        except Exception as e:  # noqa: BLE001 — report and continue to next dataset
            print(f"  ! preview failed, skipping: {e}")
            failures.append((rid, version, str(e)))
            continue

        for table, stats in info.get("tables", {}).items():
            rows = stats.get("row_count", "?")
            size = stats.get("total_asset_size_mb", 0.0)
            print(f"    {table:40s} {rows:>8} rows, {size:>10.1f} MB assets")

        if args.dry_run:
            print("  [DRY RUN] skipping download.")
            continue

        try:
            result = ml.cache_dataset(spec, materialize=materialize)
            print(f"  cached. {result}")
        except Exception as e:  # noqa: BLE001 — report and continue to next dataset
            print(f"  ! cache failed: {e}")
            failures.append((rid, version, str(e)))

    if failures:
        print(f"\n{len(failures)} of {len(pairs)} dataset(s) failed:")
        for rid, version, err in failures:
            print(f"  - {rid} v{version}: {err}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

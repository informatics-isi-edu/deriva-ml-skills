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

**To warm more than one dataset, pass them all to a single invocation**
(repeat ``--dataset-rid`` with a paired ``--version`` each) — this is
the preferred way, rather than running the script once per dataset or
launching several runs in parallel. They are warmed **sequentially**:
each dataset's asset download is already concurrent inside the library
(``cache_dataset`` fetches asset files ~8-way by default), which
saturates a typical uplink on its own, so parallel runs would just
split the same bandwidth and contend, not go faster. One sequential
invocation also keeps progress legible and isolates a bad RID (it is
reported and skipped, the rest still warm) with a single pass/fail
summary at the end.

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
import re
import sys
import time

# Matches the library's per-file progress message, e.g.
# "Materializing bag: 120 of 4210 file(s) downloaded." — the only progress
# signal the library exposes (file counts, not bytes; see deriva-ml#314). We
# parse current/total out of it to add a percentage and to throttle the rate.
_PROGRESS_RE = re.compile(r"(?P<verb>Materializing|Validating) bag: (?P<cur>\d+) of (?P<total>\d+)")


class _ThrottledProgressHandler(logging.Handler):
    """Surface the library's file-count progress, throttled, with a percentage.

    Records that match the progress message are re-emitted at most once per
    ``interval`` seconds (always emitting the first and the final 100% line),
    with a ``(P%)`` appended. Any record that does NOT match the expected
    format is passed through unchanged, so a future change to the library's
    message wording degrades gracefully (you still see the raw line) rather
    than silently dropping progress.
    """

    def __init__(self, interval: float):
        super().__init__(level=logging.INFO)
        self.interval = interval
        self._last_emit = 0.0

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        m = _PROGRESS_RE.search(msg)
        if not m:
            # Non-progress INFO line (or changed format) — pass through.
            print(msg)
            return
        cur, total = int(m.group("cur")), int(m.group("total"))
        is_last = total > 0 and cur >= total
        now = time.monotonic()
        # Always show the final (100%) line; otherwise honor the interval.
        if not is_last and (now - self._last_emit) < self.interval:
            return
        self._last_emit = now
        pct = (cur / total * 100.0) if total else 0.0
        print(f"  {m.group('verb')}: {cur}/{total} files ({pct:.0f}%)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--dataset-rid", action="append", required=True, dest="dataset_rids",
                        help="A Dataset RID to warm. For MORE THAN ONE dataset, "
                             "repeat this (with a paired --version each, same order) "
                             "in a SINGLE invocation — that is the preferred way; do "
                             "not run the script once per dataset or in parallel.")
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
                        help="Suppress the per-dataset file-count progress lines. "
                             "Progress is on by default.")
    parser.add_argument("--progress-interval", type=float, default=15.0,
                        metavar="SECONDS",
                        help="Minimum seconds between progress lines (default 15). "
                             "Throttles the library's per-file logging so a long "
                             "warm reports on a steady cadence instead of spamming "
                             "a line per file. 0 = every update.")
    args = parser.parse_args()

    if len(args.dataset_rids) != len(args.versions):
        parser.error(
            f"--dataset-rid given {len(args.dataset_rids)} time(s) but --version "
            f"given {len(args.versions)} time(s); they must be paired one-to-one "
            f"in the same order."
        )

    # Surface the library's file-count progress, throttled and with a percentage,
    # unless suppressed. The library only emits file counts (not bytes/percent;
    # see deriva-ml#314), via INFO logging — so we attach a handler that parses
    # those records, throttles them to --progress-interval, and appends (P%).
    if not args.quiet:
        lib_logger = logging.getLogger("deriva_ml")
        lib_logger.setLevel(logging.INFO)
        lib_logger.addHandler(_ThrottledProgressHandler(args.progress_interval))
        lib_logger.propagate = False  # don't double-print via the root logger

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

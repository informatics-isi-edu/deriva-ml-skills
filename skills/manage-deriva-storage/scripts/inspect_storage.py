#!/usr/bin/env python3
"""List what DerivaML has cached on the local machine.

Reports the three local-storage species — cached dataset bags, cached
assets, and execution working directories — plus a one-line summary,
resolving against whatever cache the DerivaML object is configured to
use. Pass ``--cache-dir`` when the cache is NOT under the default
``~/.deriva-ml`` (shared clusters, fast-SSD caches, multi-user shared
caches); otherwise the default location is used.

This is a Python-only operation because the cache lives on the
caller's machine, not the MCP server's filesystem. There is
deliberately no MCP tool for it (see
``deriva-ml-mcp-plugin/docs/adr/0001-local-storage-management-out-of-mcp-scope.md``).

Read-only: this script never deletes anything. To free space, use the
deletion APIs documented in the manage-deriva-storage skill
(``ml.delete_cached_bag``, ``ml.clear_cache``, ``ml.gc_executions``).

Requires deriva-ml >= 1.46 for the typed introspection API
(``list_cached_bags`` / ``list_cached_assets`` / ``list_execution_dirs``
/ ``get_storage_summary``).

Example:
    uv run python src/scripts/inspect_storage.py \\
        --hostname dev.eye-ai.org --catalog-id 5 \\
        --cache-dir /fast-ssd/deriva-cache
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Local cache directory, if not the default ~/.deriva-ml. Pass the "
             "same value your DerivaML(...) / hydra default_deriva(...) config "
             "uses, or the listing will report the wrong (default) location.",
    )
    parser.add_argument(
        "--species",
        choices=["all", "bags", "assets", "executions", "summary"],
        default="all",
        help="Which storage species to list (default: all).",
    )
    args = parser.parse_args()

    from deriva_ml import DerivaML

    # cache_dir is only passed when supplied, so the library applies its own
    # default (~/.deriva-ml/{host}/{catalog}/cache) when the user did not
    # relocate the cache.
    kwargs = {"cache_dir": args.cache_dir} if args.cache_dir else {}
    ml = DerivaML(args.hostname, args.catalog_id, **kwargs)

    want = args.species

    if want in ("all", "bags"):
        print("== Cached dataset bags ==")
        try:
            bags = list(ml.list_cached_bags())
        except (PermissionError, OSError) as e:
            print(f"  ! could not read the bag cache: {e}")
            print("  ! a cached bag directory is unreadable (permissions?) — "
                  "fix access or remove that directory, then re-run.")
            bags = []
        if not bags:
            print("  (none)")
        for b in bags:
            size_mb = (b.size_bytes or 0) / 1e6
            print(f"  {b.dataset_rid:>10}  v{b.version:<12} {b.status.value:<22} "
                  f"{size_mb:>10.1f} MB  {b.path}")

    if want in ("all", "assets"):
        print("== Cached assets ==")
        try:
            assets = list(ml.list_cached_assets())
        except (PermissionError, OSError) as e:
            print(f"  ! could not read the asset cache: {e}")
            print("  ! a cached asset directory is unreadable (permissions?) — "
                  "fix access or remove that directory, then re-run.")
            assets = []
        if not assets:
            print("  (none)")
        for a in assets:
            size_mb = (a.size_bytes or 0) / 1e6
            print(f"  {a.rid:>10}  md5={a.md5:<34} {size_mb:>10.1f} MB  {a.path}")

    if want in ("all", "executions"):
        print("== Execution working directories ==")
        try:
            dirs = list(ml.list_execution_dirs())
        except (PermissionError, OSError) as e:
            print(f"  ! could not read execution working directories: {e}")
            print("  ! an execution directory is unreadable (permissions?) — "
                  "fix access or remove that directory, then re-run.")
            dirs = []
        if not dirs:
            print("  (none)")
        for d in dirs:
            print(f"  {d['execution_rid']:>10}  {d['size_mb']:>10.1f} MB  {d['path']}")

    if want in ("all", "summary"):
        try:
            s = ml.get_storage_summary()
        except (PermissionError, OSError) as e:
            print("== Summary ==")
            print(f"  ! could not compute storage summary: {e}")
            print("  ! an unreadable cache/execution directory blocked the size "
                  "walk — fix access or remove it, then re-run.")
            return 0
        print("== Summary ==")
        print(f"  bags:       {s['bag_count']:>4}  ({s['bag_size_mb']:.1f} MB)")
        print(f"  assets:     {s['asset_count']:>4}  ({s['asset_size_mb']:.1f} MB)")
        print(f"  exec dirs:  {s['execution_dir_count']:>4}  ({s['execution_size_mb']:.1f} MB)")
        print(f"  total:      {s['total_size_mb']:.1f} MB")

    return 0


if __name__ == "__main__":
    sys.exit(main())

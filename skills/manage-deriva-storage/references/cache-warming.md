# Cache-Warming Recipes

Full cache-warming recipes for Phase 3 (Pre-fetch — warm the cache):
dataset bag, metadata-only, single asset, verify. See `SKILL.md` for the
Pre-flight Pattern summary and the pointer here.

Download datasets or assets into the local cache **without creating an execution**. Useful before long-running experiments to avoid download delays mid-run.

## Cache a dataset bag

> **Run the `warm_cache.py` script — do NOT hand-write inline cache-warming Python.** This is the one bypass to actively resist: the script gives you `--dry-run`, `--metadata-only`, `--cache-dir`, and a stable CLI, and (when committed) makes the warm step reproducible — a one-off `ml.cache_dataset(...)` snippet gives none of that and leaves no trace. (This is about *script vs. inline*, a separate question from *where you run the script* — see the two run modes just below. Read-only *inspection* — `inspect_storage.py` / a quick `ml.list_cached_bags()` — is exempt: run in place, inline is fine. This rule is about *warming*.)
>
> | Rationalization (STOP — you're about to bypass) | Reality |
> |---|---|
> | "I already know how to call `ml.cache_dataset()`" | Knowing the API is exactly the trap. The script wraps it with `--dry-run`, `--metadata-only`, `--cache-dir`, and a stable CLI you don't have to reconstruct. |
> | "Inline Python is faster / fewer steps" | Running the bundled script in place (Mode 1 below) is just as fast and needs no copying — you get the CLI for free with no extra steps. |
> | "Writing it inline avoids copying a file" | You don't have to copy it — run it in place from `${skill_base_dir}` (Mode 1). Copying is only for when you want it committed (Mode 2). |
>
> If you catch yourself reaching for inline `cache_dataset` / `download_dataset_bag` to warm the cache: stop and run `warm_cache.py` instead (in place is fine).

`warm_cache.py` has **two run modes** — and "use the script" (the rule above) does NOT mean "you must copy it first." These are independent decisions:

**Mode 1 — run it in place, now (the default for a one-off warm).** When the user just wants the cache warmed for the work at hand, **you run the bundled script directly from this skill's directory — don't hand the command off to the user, and don't copy anything.** Same as `inspect_storage.py`:

```bash
uv run python ${skill_base_dir}/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0
```

The single `--dataset-rid` above is just the one-dataset case. **For two or more datasets, don't repeat this command — pass all the pairs to one call** (see "Warming several datasets" below).

**Mode 2 — copy into the project, for reproducibility.** When the warm step is part of the experiment's repeatable setup (it'll run again — before each training run, in CI, across a sweep), copy it from `${skill_base_dir}/scripts/warm_cache.py` into `src/scripts/` and commit it, then run the copied version:

```bash
uv run python src/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0
```

Both modes run the *same* script — the only difference is whether it gets committed. Mode 1 is the right default when the user asks you to warm the cache; reach for Mode 2 when the warm belongs in the project's permanent setup. Either way: it's the script, not a hand-written `cache_dataset()` snippet (see the rule above).

**Warming several datasets — pass them all to one invocation (the preferred way).** When more than one dataset needs warming, give a single `warm_cache.py` call repeated `--dataset-rid` / `--version` pairs (same order) — **not** one run per dataset, and **not** several runs in parallel. One call is preferable on every axis:

- It warms each dataset with the library's built-in ~8-way asset concurrency, one after another — which already saturates a typical uplink. Parallel processes (or `&`-backgrounded runs) just split the same bandwidth and contend, so they're no faster and usually slower.
- A bad RID (deleted catalog, dev-label version) is reported and **skipped**, and the remaining datasets still warm — you get one consolidated pass/fail summary instead of N separate exit codes to babysit.
- It's one command to read, log, and (in Mode 2) commit.

So the rule: **more than one dataset → one `warm_cache.py` call with all the pairs.** Reach for separate invocations only when the datasets genuinely belong to different catalogs (different `--hostname`/`--catalog-id`).

```bash
uv run python ${skill_base_dir}/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 1.0.0 \
    --dataset-rid 3WSE --version 2.1.0 \
    --dataset-rid 9QPM --version 0.4.0
```

**Progress.** For a multi-GB warm, the script reports per-dataset progress by default — `Materializing: 120/4210 files (3%)` lines — so it isn't a silent wait. The progress is **throttled**: by default one line at most every 15 s (tune with `--progress-interval SECONDS`; `0` = every update), with the first and final (100%) lines always shown, so a long warm reports on a steady cadence instead of spamming a line per file. It is **file-count** progress, not bytes/percent (the library exposes file counts only; true byte progress would need a deriva-ml change — tracked at [deriva-ml#314](https://github.com/informatics-isi-edu/deriva-ml/issues/314)), so the percentage is *files done*, which can be lumpy when a few large files dominate. Pass `--quiet` to suppress progress entirely.

Note for the agent: the script does not draw a live, redrawing progress bar — it emits discrete throttled lines, which is the right shape when Claude runs it through the Bash tool (captured output, not a live terminal). Relay the latest line's milestone to the user rather than expecting an animated bar.

**What the output looks like** (so you can relay status to the user, not dump raw text):

```
[1/3] 28CT v1.0.0
    Image                                       4210 rows,     1834.2 MB assets
    Subject                                      512 rows,        0.0 MB assets
  Materializing: 120/4210 files (3%)
  Materializing: 2380/4210 files (57%)
  Materializing: 4210/4210 files (100%)
  cached. {'status': 'cached_materialized', ...}
[2/3] 3WSE v2.1.0
  ! preview failed, skipping: 404 ... catalog 27
[3/3] 9QPM v0.4.0
    ...
  cached. {...}

1 of 3 dataset(s) failed:
  - 3WSE v2.1.0: 404 ... catalog 27
```

Read it as: `[i/N] <rid> <version>` headers track which dataset; a `! ... skipping` / `! cache failed` line means *that* dataset failed but the rest continued; the final `X of N dataset(s) failed:` block (and exit code 1) is the consolidated result. Report the substance to the user (e.g. *"2 of 3 cached; 9QPM failed — its catalog is gone"*), not the raw stream.

**Keeping a record of a long warm.** There's no `--log-file` flag — you don't need one. For a long multi-GB / many-dataset warm where the user steps away, capture the stream with the shell:

```bash
uv run python ${skill_base_dir}/scripts/warm_cache.py ... 2>&1 | tee warm-cache.log
```

`tee` shows progress live *and* writes `warm-cache.log` for later review. Only do this for genuinely long warms; a quick one-off doesn't need a log file cluttering the directory.

Downloads the full bag (including materialized assets) into the cache. Subsequent calls to `exe.download_dataset_bag(spec)` with the same RID and version reuse the cached copy.

## Cache metadata only (no asset files)

Add `--metadata-only` to skip asset bytes:

```bash
uv run python src/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0 \
    --metadata-only
```

Useful for inspecting schema and row counts before committing to a full download.

The template wraps this underlying call — `ml.cache_dataset(spec, materialize=True)`:

```python
from deriva_ml.dataset.aux_classes import DatasetSpec
spec = DatasetSpec(rid="28CT", version="0.9.0")
ml.cache_dataset(spec, materialize=True)
```

Shown so you recognize what the script runs — **not as an invitation to skip it.** Per the red-flags table above, warming goes through `warm_cache.py` (run it in place for a one-off, or copy + commit it for repeatable setup). The only time the bare call is appropriate is a genuinely throwaway exploration in a notebook you will not commit — and even then, running the script in place is just as easy.

## Cache an individual asset

Individual-asset download is a Python-API operation. Pass the asset RID to `Execution.download_asset()` from inside an execution context, or call it through a bundled script template — there is no MCP tool that warms a single asset to the user's machine.

```python
exe.download_asset("3WSE")  # pre-trained model weights, etc.
```

## Verify cache after pre-fetching

```
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="28CT", version="0.9.0")
```

Confirm `cache_status` is `cached_materialized`.

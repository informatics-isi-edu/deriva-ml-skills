#!/usr/bin/env python3
"""COPY-ME template: the data-source layer for a from-scratch load.

`stage_source()` is the ONE place your dataset-specific source logic lives —
download, copy, extract, decode — whatever it takes to land your raw files on
disk in the layout the rest of the loader expects. Everything downstream
(register, upload) is generic and needs no edit for a standard layout.

THE LAYOUT CONTRACT (what stage_source MUST produce):

    SOURCE_ROOT/
        <PARTITION>/        # one subdir per entry in PARTITIONS
            <file>          #   e.g. SOURCE_ROOT/train/img_001.png
            ...
        <LABEL_MANIFEST>    # optional: a labels file at the root, if used

  - PARTITIONS is a list you set in the orchestrator config. Common shapes:
      ["train", "test"]   — a train/test split on the source side
      ["."]               — a flat layout (all files directly under SOURCE_ROOT)
  - If you use a label manifest, write it at SOURCE_ROOT/<LABEL_MANIFEST>
    (e.g. a CSV of filename,label). The register phase registers it as a File
    so the upload phase can read it back across the execution boundary — no
    in-memory label state has to cross executions.

(Worked instance: the CIFAR-10 reference downloads the Toronto archive, decodes
the pickles, and writes sampled PNGs into train/ and test/ plus a labels.csv —
all of that lives in ITS stage_source, none of it here.)
"""

from __future__ import annotations

from pathlib import Path


def stage_source(
    source_root: Path,
    partitions: list[str],
    label_manifest: str | None = None,
) -> Path:
    """Populate ``source_root`` with the files to ingest, per the layout contract.

    Replace the body with your data source. The contract: after this returns,
    each ``source_root/<partition>/`` exists and holds the files to ingest, and
    (if ``label_manifest`` is set) ``source_root/<label_manifest>`` exists.

    Args:
        source_root: Root directory to stage files under (created if absent).
        partitions: Subdirectory names to create under ``source_root``. Use
            ``["."]`` for a flat layout.
        label_manifest: Optional filename to write at ``source_root`` (e.g.
            ``"labels.csv"``); ``None`` if labels come from elsewhere.

    Returns:
        ``source_root`` (now populated).
    """
    source_root = Path(source_root).expanduser()
    source_root.mkdir(parents=True, exist_ok=True)
    for partition in partitions:
        (source_root / partition).mkdir(parents=True, exist_ok=True)

    # TODO: your data source — download / copy / extract / decode your raw
    #   files into source_root/<partition>/ for each partition above. If you
    #   use a label manifest, write it to source_root / label_manifest here.
    raise NotImplementedError(
        "Implement stage_source for your data source — see the layout contract "
        "in this module's docstring."
    )

    return source_root  # reached once you remove the raise above

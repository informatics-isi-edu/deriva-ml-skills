# Asset Concepts

Background on assets in DerivaML. For the step-by-step guide, see `workflow.md`.

## Table of Contents

- [What is an Asset?](#what-is-an-asset)
- [Asset Tables](#asset-tables)
- [Asset RIDs](#asset-rids)
- [Asset Types](#asset-types)
- [Object Storage](#object-storage)
- [How Assets Are Uploaded](#how-assets-are-uploaded)
- [Asset Caching](#asset-caching)
- [Asset Provenance](#asset-provenance)
- [Built-in Asset Tables](#built-in-asset-tables)
  - [Execution Metadata vs Execution Assets](#execution-metadata-vs-execution-assets)
  - [Notebook Output Assets](#notebook-output-assets)

---

## What is an Asset?

An asset is a file-based record in a Deriva catalog. Each asset combines a file (stored in Deriva's object store) with catalog metadata — filename, size, checksum, description, and any custom columns defined on the asset table.

An asset can be **any file** that needs to be tracked in the catalog — input files, output files, or reference files. Common examples include:

**Input data:**
- **Images** — microscopy slides, X-rays, CT scans, photographs, satellite imagery
- **Documents** — PDFs, clinical reports, text corpora
- **Raw data files** — DICOM files, FASTA sequences, sensor readings

**Model artifacts:**
- **Model weights** — trained PyTorch `.pt`, TensorFlow `.h5`, ONNX checkpoints
- **Embeddings** — precomputed feature vectors, word embeddings
- **Tokenizer files** — vocabulary files, sentencepiece models

**Experiment outputs:**
- **Prediction files** — CSVs of model outputs (class probabilities, confidence scores)
- **Segmentation masks** — pixel-level annotation overlays
- **Plots and figures** — ROC curves, confusion matrices, training loss charts
- **Evaluation metrics** — JSON/CSV files with accuracy, F1, AUC results

**Reference files:**
- **Configuration files** — YAML/JSON experiment configs, hyperparameter snapshots
- **Checksums and manifests** — integrity verification files
- **Documentation** — analysis notebooks (executed `.ipynb` and `.md` conversions)

Assets are the bridge between files on disk and structured catalog data. Unlike raw files, assets have identity (RIDs), provenance (which execution created them), types (vocabulary-based categorization), and relationships (foreign keys to other tables).

### Assets vs Datasets

Assets and datasets serve different purposes:

| | **Asset** | **Dataset** |
|---|---|---|
| **What it is** | A single file with metadata | A versioned collection of catalog records |
| **Contains** | One file (image, model weight, CSV, etc.) | References to many records across tables |
| **Storage** | File in object store + metadata row in an asset table | Membership associations in the catalog |
| **Versioning** | Immutable once uploaded (new version = new asset) | Semantic versioning with snapshot semantics |
| **Primary use** | Track individual files with provenance | Organize data for reproducible experiments |
| **Download** | Python API `ml.download_asset(rid)` → one file | Python API `dataset.download_dataset_bag(version)` → BDBag with all members + assets |

**Key distinction:** A dataset *contains* assets (among other records). When you download a dataset as a BDBag, the bag includes all asset files reachable from the dataset's members. But an asset exists independently — you can download, reference, and track a single asset without it being part of any dataset.

**When to use which:**
- Use **assets** when you need to track individual files (model weights, prediction CSVs, uploaded images)
- Use **datasets** when you need a versioned, reproducible collection (training data, test sets, labeled image batches)

## Asset Tables

An asset table is a catalog table with special columns for file management. When you create an asset table, DerivaML automatically adds these **standard asset columns**:

| Column | Type | Description |
|--------|------|-------------|
| `Filename` | text | Original filename (e.g., `model_weights.pt`) |
| `URL` | text | Object store URL (set automatically on upload) |
| `Length` | int | File size in bytes |
| `MD5` | text | MD5 checksum for integrity verification |
| `Description` | text | Optional human-readable description |

In addition to these standard columns, asset tables can have **custom metadata columns** — for example, an `Image` table might add `Width`, `Height`, and `Format` columns, or a `Model` table might add `Architecture` and `Epochs`.

Asset tables also get automatically created **association tables**:
- An **Asset_Type association** — links each asset to vocabulary terms categorizing it
- An **Execution association** — tracks which executions created or used each asset, with a role of "Input" or "Output"

## Asset RIDs

Every asset has a unique **RID** (Resource IDentifier) — a short, immutable string like `3-JSE4` or `2-IMG1`. RIDs are the primary way to reference assets across the system:

- **In MCP tools**: Pass `asset_rid` to Python API `ml.download_asset(rid)`, `list_asset_executions`, etc.
- **In configurations**: Use RIDs in `AssetSpecConfig` to specify execution inputs
- **In provenance**: Execution records reference asset RIDs for inputs and outputs
- **In the web UI**: Each asset's Chaise page URL includes its RID
- **In citation**: `ml.cite(rid)` generates a permanent URL for an asset

RIDs are assigned by the catalog when a record is created and never change. Use RIDs (not filenames or URLs) as the stable identifier for assets.

## Asset Types

Assets are categorized using the **Asset_Type** controlled vocabulary. Each asset can have multiple types (e.g., an image could be both "Training_Data" and "Augmented").

Asset types serve two purposes:
1. **Organization** — filter and browse assets by category in the web UI
2. **Configuration** — specify which types of assets an execution expects

Custom asset types can be created for domain-specific categorization. When you create a new asset table, DerivaML automatically adds the table name as a term in the Asset_Type vocabulary.

## Object Storage

Files are stored in Deriva's object store. When you upload an asset, the file goes to the object store and the catalog record gets a URL pointing to it. When you download an asset, DerivaML fetches the file from the object store using that URL.

You never interact with the object store directly — DerivaML handles all file transfers. The `URL` column in asset tables contains the storage path, but you use RIDs and MCP tools for all operations.

## How Assets Are Uploaded

Assets are created as part of the execution lifecycle — you register files during an execution, and they're uploaded in batch when the execution completes. This ensures every asset has provenance (which execution created it).

### The upload flow

1. **Register the file** — call `asset_file_path(asset_name, file_name)` during an execution. This:
   - Stages the file in the execution's working directory
   - Records the target asset table and file metadata
   - Returns a file path — write your output to this path

2. **Write to the path** — save your model weights, predictions, plots, etc. to the returned path

3. **Upload all at once** — call `upload_execution_outputs()` after the execution completes. This:
   - Uploads each staged file to the object store
   - Computes the MD5 checksum automatically
   - Records the file size (Length) automatically
   - Creates asset records in the catalog with Filename, URL, Length, MD5
   - Links each asset to the execution with role "Output"
   - Applies any asset types specified during registration

### What metadata is captured automatically

| Field | How it's set |
|-------|-------------|
| `Filename` | From the file name provided to Python API `exe.asset_file_path()` |
| `URL` | Set by the upload process (object store path) |
| `Length` | Computed from the file size during upload |
| `MD5` | Computed from the file content during upload |
| `Execution` | Linked to the active execution automatically |

Custom metadata columns (e.g., `Width`, `Height`, `Architecture`) must be set separately after upload, or can be set programmatically in the Python API.

## Asset Caching

For large assets that are reused across multiple executions (e.g., pretrained model weights), DerivaML supports **checksum-based caching**. When an asset is specified with `cache=True` in an execution configuration, DerivaML:

1. Checks the local cache directory for a file matching the asset's MD5 checksum
2. If found, creates a symlink to the cached copy instead of re-downloading
3. If not found, downloads the file and stores it in the cache for future use

The cache key is `{rid}_{md5}`, so if an asset's file is updated (new MD5), the old cached copy is not reused.

In hydra-zen configurations:
```python
from deriva_ml.asset.aux_classes import AssetSpecConfig

AssetSpecConfig(rid="6-EPNR", cache=True)   # Cached — reused across executions
AssetSpecConfig(rid="6-EP56", cache=False)   # Not cached — downloaded each time
```

Use caching for large, immutable assets like pretrained weights. Avoid caching for assets that change between runs.

## Asset Provenance

Every asset is linked to the executions that created or used it through an association table with an **Asset_Role** column:

- **Output** — the execution created this asset (e.g., a training run produced model weights)
- **Input** — the execution consumed this asset (e.g., an analysis notebook read prediction CSVs)

This bidirectional tracking means you can answer two key questions:
- "Where did this asset come from?" — find the execution with role "Output"
- "What used this asset?" — find all executions with role "Input"

Provenance is recorded automatically: uploading via Python API `exe.upload_execution_outputs()` records "Output" links, and downloading via Python API `ml.download_asset(rid)` within an execution records "Input" links.

## Built-in Asset Tables

DerivaML catalogs include two built-in asset tables in the `deriva-ml` schema:

| Table | Purpose |
|-------|---------|
| `Execution_Asset` | General-purpose output files from executions (model weights, predictions, plots). The default target when no specific asset table is specified. |
| `Execution_Metadata` | Auto-managed metadata files (configuration snapshots, logs). Written automatically by the execution framework — you typically don't interact with this directly. |

Domain-specific asset tables (e.g., `Image`, `Model`, `Slide`) are created in the domain schema as needed for each project.

### Execution Metadata vs Execution Assets

The `Execution_Metadata` and `Execution_Asset` tables serve different roles:

**Execution_Metadata** stores auto-generated files that the execution framework creates for every execution. You do not upload these yourself — they are written automatically. There are four metadata types:

| Metadata Type | Contents |
|---------------|----------|
| `Deriva_Config` | The resolved DerivaML configuration as a JSON file (catalog connection, execution parameters) |
| `Hydra_Config` | The Hydra/hydra-zen configuration snapshot as a YAML file (all resolved config values) |
| `Execution_Config` | The `uv.lock` file capturing the exact Python dependency versions used |
| `Runtime_Env` | A snapshot of the runtime environment (Python version, platform, environment variables) |

These metadata files ensure full reproducibility — given the same code commit and metadata, an execution can be recreated exactly.

**Execution_Asset** stores user output files — the artifacts your code explicitly produces. These are the files you register with `exe.asset_file_path()` and upload with `exe.upload_execution_outputs()`. Examples include model weights, prediction CSVs, plots, and evaluation metrics.

**Key distinction:** Execution_Metadata is written by the framework (you never create these entries). Execution_Asset is written by your code (you explicitly register and upload these files).

### Notebook Output Assets

When running notebooks via `deriva-ml-run-notebook`, the framework automatically uploads two output files as `Execution_Asset` entries after the notebook completes:

| Output | Description |
|--------|-------------|
| The executed `.ipynb` file | The full notebook with all cell outputs (plots, tables, printed values) |
| A converted `.md` file | A Markdown version of the executed notebook, suitable for quick review without Jupyter |

These are uploaded automatically — you do not need to call `exe.asset_file_path()` or `exe.upload_execution_outputs()` for them. They appear as `Execution_Asset` records linked to the notebook's execution with role "Output".

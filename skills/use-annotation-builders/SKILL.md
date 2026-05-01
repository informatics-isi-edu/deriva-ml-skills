---
name: use-annotation-builders
description: "Write Python scripts using type-safe annotation builder classes (ColumnAnnotation, TableAnnotation, KeyAnnotation) for production Deriva catalog code. Use when writing Python code to configure catalog display, not when using interactive MCP tools."
disable-model-invocation: true
---

# Using Annotation Builder Classes

DerivaML provides Python builder classes for constructing Deriva annotations with full type safety and IDE autocompletion. These are ideal for production code, scripts, and notebooks where you need programmatic control over catalog annotations.

**This skill covers the Python builder class approach.** For quick interactive setup using MCP tools (better for one-off tweaks and exploration), see the `customize-display` skill instead.

> **Requires:** the `deriva-ml` Python package, which ships the annotation builder classes (`from deriva_ml.model.annotations import Display, VisibleColumns, ...`). The annotations themselves are core Chaise concepts that work on any Deriva catalog, but the typed Python wrappers currently live in the deriva-ml package. If you only have `deriva-py` installed, use the `customize-display` skill (MCP tools — no Python imports required) or write annotations as plain dicts.


## Connection model

Builders run inside Python code that has constructed a `DerivaML` instance — that instance owns the catalog connection. The Python builder pattern stages edits on the local model and commits them with `ml.apply_annotations()` (this is a Python API call, NOT an MCP tool).

> **Note:** The MCP-side `apply_annotations` tool was removed in `deriva-mcp-core` (annotations apply immediately when set via MCP). The Python `ml.apply_annotations()` call documented in this skill is a separate concept — it commits the locally-staged builder edits to the catalog. The two patterns are distinct: MCP tools are immediate-apply; Python builders stage then apply.

## When to Use Builders vs MCP Tools

| Use Case | Approach |
|----------|----------|
| Interactive catalog setup | MCP tools (`set_visible_columns`, `set_row_name_pattern`, etc.) — immediate apply |
| One-off display tweaks | MCP tools |
| Production deployment scripts | Builders + `ml.apply_annotations()` |
| Reusable catalog configuration | Builders |
| Complex pseudo-columns and facets | Builders |
| Code that needs IDE autocompletion | Builders |
| Sharing configuration across catalogs | Builders |

## Available Builder Classes

All builders are imported from `deriva_ml.model.annotations` (or `deriva_ml.model` for convenience) and follow the same pattern: construct, configure, call `.to_dict()`, assign to `table.annotations[Builder.tag]`, then `ml.apply_annotations()`.

| Builder | Purpose |
|---------|---------|
| `Display` | Table/column display names and markdown patterns |
| `VisibleColumns` | Which columns appear in each Chaise context |
| `VisibleForeignKeys` | Which related tables appear on the detail page |
| `TableDisplay` | Row naming patterns, sort order, page size |
| `ColumnDisplay` | Per-column value formatting and rendering |
| `PseudoColumn` | Computed values and FK-traversed columns |
| `FacetList` / `Facet` | Faceted search panel configuration |

Context constants (e.g., `CONTEXT_COMPACT`, `CONTEXT_DETAILED`, `CONTEXT_ROW_NAME`) are module-level variables, not a class.

Helpers: `OutboundFK`, `InboundFK` (FK path navigation), `Aggregate` (COUNT, ARRAY, MIN, MAX, etc.).

Handlebars templates (`{{{Column}}}`) are used in row name patterns and markdown patterns. Use `validate_template_syntax`, `get_handlebars_template_variables`, and `preview_handlebars_template` to test patterns.

For the full API reference of each builder class, see `references/builder-api.md`.

## Complete Example: Configuring an Image Table

```python
from deriva_ml import DerivaML
from deriva_ml.model.annotations import (
    Display, VisibleColumns, VisibleForeignKeys, TableDisplay,
    ColumnDisplay, PseudoColumn, OutboundFK, InboundFK,
    Aggregate, FacetList, Facet,
    CONTEXT_COMPACT, CONTEXT_DETAILED, CONTEXT_ROW_NAME,
)

ml = DerivaML(hostname, catalog_id)

# Table display name
display = Display(name="Images", markdown_name="**Images**")

# Visible columns per context
vc = VisibleColumns()

# Pseudo-column: subject name via FK
subject_name = PseudoColumn(
    source=[OutboundFK("deriva-ml", "Image_Subject_fkey"), "Name"],
    markdown_name="Subject"
)

# Pseudo-column: diagnosis via FK chain
diagnosis = PseudoColumn(
    source=[
        OutboundFK("deriva-ml", "Image_Subject_fkey"),
        OutboundFK("deriva-ml", "Subject_Diagnosis_fkey"),
        "Name"
    ],
    markdown_name="Diagnosis"
)

vc.set(CONTEXT_COMPACT, [
    "Filename",
    subject_name.to_dict(),
    diagnosis.to_dict(),
    "Image_Type"
])

vc.set(CONTEXT_DETAILED, [
    "Filename",
    subject_name.to_dict(),
    diagnosis.to_dict(),
    "Image_Type",
    "URL",
    "File_Size",
    "Width",
    "Height",
    "Description"
])

# Table display: row name and ordering
td = TableDisplay()
td.set_row_name(CONTEXT_ROW_NAME, "{{{Filename}}}")
td.set_row_order(CONTEXT_COMPACT, [{"column": "Filename", "descending": False}])

# Column display: render URL as download link
url_display = ColumnDisplay()
url_display.set(CONTEXT_COMPACT, markdown_pattern="[Download]({{{URL}}})")

# Facets for filtering
facets = FacetList()
facets.add(Facet(
    source=[OutboundFK("deriva-ml", "Image_ImageType_fkey"), "Name"],
    markdown_name="Image Type",
    open=True
))
facets.add(Facet(
    source=[OutboundFK("deriva-ml", "Image_Subject_fkey"), "Name"],
    markdown_name="Subject"
))

# Visible foreign keys on detail page
vfk = VisibleForeignKeys()
vfk.set(CONTEXT_DETAILED, [
    {"source": [{"inbound": ["deriva-ml", "Feature_Value_Image_fkey"]}, "RID"]}
])

# Apply all annotations to the table
table = ml.model.schemas["deriva-ml"].tables["Image"]
table.annotations[Display.tag] = display.to_dict()
table.annotations[VisibleColumns.tag] = vc.to_dict()
table.annotations[TableDisplay.tag] = td.to_dict()
table.annotations[VisibleForeignKeys.tag] = vfk.to_dict()
table.annotations[FacetList.tag] = facets.to_dict()

# Apply column-level annotation
table.columns["URL"].annotations[ColumnDisplay.tag] = url_display.to_dict()

# Push all changes to the catalog
ml.apply_annotations()
```

## Reference Resources

For detailed reference material beyond what this skill covers, read these MCP resources:

- `deriva://docs/annotation-contexts` — Complete JSON reference of all valid Chaise annotation contexts and their usage. Read this when you need the full list of contexts or want to understand context inheritance.
- `deriva://docs/annotations` — Full guide to annotation builders and the underlying JSON structure. Read this for advanced pseudo-column source syntax, facet options, or pre-format directives.
- `deriva://docs/chaise/config` — Chaise web UI configuration beyond annotations. Read this for navbar customization, default page sizes, or login configuration.

To inspect current annotations on a specific table or column:
- `deriva://table/{table_name}/annotations` — Display-related annotations currently set on a table
- `deriva://table/{table_name}/column/{column_name}/annotations` — Display-related annotations on a column

## Related Skills

- **`customize-display`** — For applying annotations using MCP tools (without Python scripts). Use the `customize-display` skill for quick interactive annotation changes and one-off tweaks. This skill covers the Python script-based annotation builder approach for complex bulk annotations.

## Tips

- Builders produce the same JSON that MCP tools set -- they are two ways to do the same thing.
- Use builders when you need to version-control your catalog configuration in Python scripts.
- Use MCP tools for quick interactive changes.
- Always call `ml.apply_annotations()` after making builder changes. (MCP tools immediate-apply; this only applies to the Python builder pattern.)
- PseudoColumns are powerful for showing related data without changing the data model.
- Test complex Handlebars patterns with `preview_handlebars_template` before applying them.

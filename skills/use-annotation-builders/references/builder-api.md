# Annotation Builder API Reference

Detailed API documentation for each DerivaML annotation builder class. For an overview of when and how to use builders, see the parent skill (`SKILL.md`).

## Table of Contents

- [Display -- Names, Markdown, Styles](#display----names-markdown-styles)
- [VisibleColumns -- Per-Context Column Lists](#visiblecolumns----per-context-column-lists)
- [VisibleForeignKeys -- Related Table Sections](#visibleforeignkeys----related-table-sections)
- [TableDisplay -- Row Naming and Ordering](#tabledisplay----row-naming-and-ordering)
- [ColumnDisplay -- Value Formatting](#columndisplay----value-formatting)
- [PseudoColumns -- Computed and FK-Traversed Values](#pseudocolumns----computed-and-fk-traversed-values)
- [FacetList and Facet -- Faceted Search Configuration](#facetlist-and-facet----faceted-search-configuration)
- [Handlebars Templates](#handlebars-templates)
- [Context Constants](#context-constants)

---

## Display -- Names, Markdown, Styles

Controls how a table or column is displayed.

```python
from deriva_ml.model.annotations import Display

# Simple display name
display = Display(name="Labeled Images")

# With markdown pattern for row naming
display = Display(
    name="Images",
    markdown_name="**Images**",
    markdown_pattern="{{{Filename}}} ({{{Diagnosis}}})"
)

# Apply to a table
table.annotations[Display.tag] = display.to_dict()
```

## VisibleColumns -- Per-Context Column Lists

Defines which columns appear in each Chaise context, with method chaining.

```python
from deriva_ml.model.annotations import VisibleColumns, CONTEXT_COMPACT, CONTEXT_DETAILED, CONTEXT_ENTRY

vc = VisibleColumns()

# Set columns for compact view
vc.set(CONTEXT_COMPACT, [
    "Filename",
    "Subject",
    "Diagnosis",
    "Image_Type"
])

# Set columns for detailed view (more columns)
vc.set(CONTEXT_DETAILED, [
    "Filename",
    "Subject",
    "Diagnosis",
    "Image_Type",
    "URL",
    "File_Size",
    "Width",
    "Height",
    "Description"
])

# Set entry form columns
vc.set(CONTEXT_ENTRY, [
    "Filename",
    "Subject",
    "Diagnosis",
    "Image_Type",
    "Description"
])

# Apply to table
table.annotations[VisibleColumns.tag] = vc.to_dict()
```

## VisibleForeignKeys -- Related Table Sections

Controls which related tables appear on the detail page.

```python
from deriva_ml.model.annotations import VisibleForeignKeys, CONTEXT_DETAILED

vfk = VisibleForeignKeys()

vfk.set(CONTEXT_DETAILED, [
    {"source": [{"inbound": ["schema", "Image_Subject_fkey"]}, "RID"]},
    {"source": [{"inbound": ["schema", "Sample_Subject_fkey"]}, "RID"]}
])

table.annotations[VisibleForeignKeys.tag] = vfk.to_dict()
```

## TableDisplay -- Row Naming and Ordering

Controls table-level display behavior including row naming and default sort order.

```python
from deriva_ml.model.annotations import TableDisplay, CONTEXT_ROW_NAME, CONTEXT_COMPACT

td = TableDisplay()

# Row name pattern (how records appear in FK links)
td.set_row_name(CONTEXT_ROW_NAME, "{{{Last_Name}}}, {{{First_Name}}}")

# Row ordering
td.set_row_order(CONTEXT_COMPACT, [
    {"column": "Name", "descending": False}
])

# Page size
td.set_page_size(CONTEXT_COMPACT, 25)

table.annotations[TableDisplay.tag] = td.to_dict()
```

## ColumnDisplay -- Value Formatting

Controls how individual column values are rendered.

```python
from deriva_ml.model.annotations import ColumnDisplay, CONTEXT_COMPACT, CONTEXT_DETAILED

cd = ColumnDisplay()

# Render URL as a download link
cd.set(CONTEXT_COMPACT, markdown_pattern="[Download]({{{URL}}})")

# Pre-format: transform value before display
cd.set(CONTEXT_DETAILED, pre_format={"format": "%d", "unit": "bytes"})

column.annotations[ColumnDisplay.tag] = cd.to_dict()
```

## PseudoColumns -- Computed and FK-Traversed Values

PseudoColumns let you display values from related tables or computed expressions in column lists.

```python
from deriva_ml.model.annotations import PseudoColumn, OutboundFK, InboundFK, Aggregate

# Follow an outbound foreign key to show a related column
# Image -> Subject -> Name
subject_name = PseudoColumn(
    source=[
        OutboundFK("schema", "Image_Subject_fkey"),
        "Name"
    ],
    markdown_name="Subject Name"
)

# Follow an inbound foreign key with aggregation
# Count of images related to a subject
image_count = PseudoColumn(
    source=[
        InboundFK("schema", "Image_Subject_fkey"),
        "RID"
    ],
    aggregate=Aggregate.CNT_D,
    markdown_name="# Images"
)

# Array aggregation -- collect all values
all_diagnoses = PseudoColumn(
    source=[
        InboundFK("schema", "Diagnosis_Subject_fkey"),
        OutboundFK("schema", "Diagnosis_Type_fkey"),
        "Name"
    ],
    aggregate=Aggregate.ARRAY_D,
    markdown_name="Diagnoses"
)

# Use in visible columns
vc.set(CONTEXT_COMPACT, [
    "Name",
    subject_name.to_dict(),
    image_count.to_dict(),
    all_diagnoses.to_dict()
])
```

**FK path helpers:**
- `OutboundFK(schema, constraint)` -- follow FK from this table to a related table
- `InboundFK(schema, constraint)` -- follow FK from a related table to this table
- Chain multiple hops: `[OutboundFK(...), OutboundFK(...), "Column"]`

**Aggregate functions:**
- `Aggregate.CNT` -- count of values
- `Aggregate.CNT_D` -- count of unique values
- `Aggregate.ARRAY` -- array of all values
- `Aggregate.ARRAY_D` -- array of unique values
- `Aggregate.MIN`, `Aggregate.MAX` -- min/max value

## FacetList and Facet -- Faceted Search Configuration

Configure the facet panel for filtering records.

```python
from deriva_ml.model.annotations import FacetList, Facet, OutboundFK

facets = FacetList()

# Simple column facet
facets.add(Facet(
    source="Species",
    markdown_name="Species",
    open=True
))

# FK-based facet (filter by related table value)
facets.add(Facet(
    source=[OutboundFK("schema", "Image_Diagnosis_fkey"), "Name"],
    markdown_name="Diagnosis",
    open=True
))

# Range facet for numeric column
facets.add(Facet(
    source="Age",
    markdown_name="Age",
    ranges=[{"min": 0, "max": 120}]
))

# Choice facet with specific options
facets.add(Facet(
    source="Status",
    markdown_name="Status",
    choices=["Active", "Completed", "Failed"]
))

table.annotations[FacetList.tag] = facets.to_dict()
```

## Handlebars Templates

Row name patterns and markdown patterns use Handlebars syntax:

```python
# Simple column reference
pattern = "{{{Name}}}"

# Multiple columns
pattern = "{{{Last_Name}}}, {{{First_Name}}}"

# Conditional display
pattern = "{{#if Description}}{{{Description}}}{{else}}{{{Name}}}{{/if}}"

# Iteration over array values
pattern = "{{#each Diagnoses}}{{{this}}}{{#unless @last}}, {{/unless}}{{/each}}"

# URL encoding for links
pattern = "[{{{Name}}}](/chaise/record/#{{{$catalog.id}}}/Schema:Table/RID={{{$url_encode.RID}}})"
```

**Template validation tools:**
```
validate_template_syntax(template="{{{Name}}} ({{{Age}}})")
get_handlebars_template_variables(template="{{{Name}}} ({{{Age}}})")
preview_handlebars_template(template="{{{Name}}}", table_name="Subject", rid="2-XXXX")
```

## Context Constants

Use context constants instead of raw strings:

```python
from deriva_ml.model.annotations import (
    CONTEXT_DEFAULT,             # "*"
    CONTEXT_COMPACT,             # "compact"
    CONTEXT_COMPACT_BRIEF,       # "compact/brief"
    CONTEXT_COMPACT_BRIEF_INLINE,# "compact/brief/inline"
    CONTEXT_COMPACT_SELECT,      # "compact/select"
    CONTEXT_DETAILED,            # "detailed"
    CONTEXT_ENTRY,               # "entry"
    CONTEXT_ENTRY_EDIT,          # "entry/edit"
    CONTEXT_ENTRY_CREATE,        # "entry/create"
    CONTEXT_EXPORT,              # "export"
    CONTEXT_FILTER,              # "filter"
    CONTEXT_ROW_NAME,            # "row_name"
)
```

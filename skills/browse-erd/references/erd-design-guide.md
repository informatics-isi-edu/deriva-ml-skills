# ERD Browser Design Guide

## Design Philosophy

Data-focused, clinical precision. Inspired by the Chaise UI's clean, functional aesthetic but with a distinctive spatial composition that communicates structure and hierarchy visually.

## Color System

### Table Type Colors

| Type | Background | Border | Badge |
|------|-----------|--------|-------|
| Domain | white | slate-300 | slate-700 |
| ML | amber-50 | amber-300 | amber-700 |
| Vocabulary | emerald-50 | emerald-300 | emerald-700 |
| Asset | sky-50 | sky-300 | sky-700 |
| Association | zinc-50 | zinc-300 | zinc-500 |

### Edge Colors
- Default: `#cbd5e1` (slate-300) at 1px
- Highlighted (connected to selected): `#334155` (slate-700) at 2px
- Dimmed (unrelated to selected): 0.2 opacity

## Layout

- Left-to-right dagre layout (LR) — reads naturally for relationship flows
- 60px node separation, 100px rank separation
- Resizable split: 70% canvas / 30% detail panel

## Interactions

- Click node → select, populate detail panel, highlight connected edges
- Click canvas → deselect
- Escape key → deselect
- Hover node → visual feedback (shadow elevation)
- Search → live filter of visible nodes
- Filter dropdown → filter by table type, toggle association visibility

## Chaise URL Patterns

- Recordset: `https://{host}/chaise/recordset/#{catalog_id}/{schema}:{table}`
- Record: `https://{host}/chaise/record/#{catalog_id}/{schema}:{table}/RID={rid}`
- Recordedit: `https://{host}/chaise/recordedit/#{catalog_id}/{schema}:{table}`

## Future Enhancements

- SVG/PNG export of the diagram
- Configurable layout direction (TB/LR)
- Column display mode on nodes (expanded view)
- Dark mode support
- Dataset membership visualization
- Execution lineage graphs

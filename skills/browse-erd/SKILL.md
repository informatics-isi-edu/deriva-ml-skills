---
name: browse-erd
description: "Use this skill to launch an interactive ERD (Entity-Relationship Diagram) browser for the currently connected Deriva catalog. Triggers on: 'browse erd', 'show erd', 'schema diagram', 'entity relationship diagram', 'visualize schema', 'catalog diagram', 'show relationships', 'explore schema visually'. Requires an active catalog connection."
---

# Interactive ERD Browser

Launch the Schema Workbench — an interactive visual ERD for the connected catalog.

## Prerequisites

- A reachable Deriva catalog (the workbench app fetches the schema via the catalog's hostname + ID — pass these to the `--backend` and `#catalog=` URL params shown below)
- The `deriva-ml-apps` package installed (`cd ~/GitHub/deriva-ml-apps && uv sync`). This is a **separate** package from `deriva-ml`; the apps package ships visualization tools (Schema Workbench, Storage Manager, etc.) and works on any Deriva catalog regardless of whether the deriva-ml-mcp plugin is loaded.
- The Schema Workbench built (`cd ~/GitHub/deriva-ml-apps/schema-workbench && pnpm install && pnpm build`)

## Steps

### 1. Confirm catalog connection

Read `deriva://catalog/connections` to verify you're connected. Note the hostname and catalog ID.

### 2. Launch the app server

Start the app server from the command line:

```bash
cd ~/GitHub/deriva-ml-apps
uv run deriva-ml-apps serve --backend <hostname>
# Then open: http://localhost:8080/apps/schema-workbench/#catalog=<catalog_id>
```

Alternatively, if you have the reverse proxy script available:

```bash
# Start the local proxy for the Schema Workbench
cd ~/GitHub/deriva-ml-apps
uv run python -m deriva_ml_apps.proxy --backend <hostname> --port 8080
```

### 3. Tell the user

- The Schema Workbench is running at the URL shown
- They must be logged into the Deriva server in their browser for authentication to work
- The app-launcher homepage at `http://localhost:8080` shows all available apps

## Features

- **Interactive graph**: Tables as nodes, foreign keys as directed edges, dagre-based hierarchical layout
- **Color-coded nodes**: Domain (slate), ML (amber), Vocabulary (emerald), Asset (sky), Association (zinc)
- **Detail panel**: Click any table to see columns, foreign keys, sample data, and features
- **Search**: Filter tables by name or schema
- **Type filter**: Show all / domain only / ML only / vocabulary only / asset only
- **Hide associations**: Toggle to reduce clutter from junction tables
- **Chaise links**: "Open in Chaise" button for each table
- **Zoom/pan**: Mouse wheel zoom, drag to pan, minimap for navigation

## Troubleshooting

- **CORS errors**: The browser must have valid cookies for the Deriva server. Log in via Chaise first.
- **Empty graph**: Check that the catalog has tables. Try `catalog_tables(hostname=..., catalog_id=...)` to list them, or `get_table_sample_data(hostname=..., catalog_id=..., schema=..., table=...)` on a known table.
- **Auth failure**: For `localhost` catalogs, ensure the local server is running and you're logged in.

---
name: create-web-app
description: "Use when building custom web applications or visualizations to run alongside Schema Workbench and Storage Manager via the deriva-ml-apps server — data dashboards, result viewers, interactive charts, custom analysis tools. Covers registration in the app server, the proxy-based catalog access pattern, and the Claude-generates-an-app workflow. Triggers on: 'create a web app for deriva-ml', 'build a visualization', 'custom dashboard', 'register app', 'deriva-ml-apps', 'app server', 'data viewer', 'interactive chart for my data'."
disable-model-invocation: true
---

# Creating Custom Web Applications for DerivaML

Build and register custom web applications that run alongside the built-in DerivaML tools (Schema Workbench, Storage Manager). Apps are served by the `deriva-ml-apps` server and can access catalog data through the proxy.

## Prerequisite: App Server

The `deriva-ml-apps` server must be installed and running. Install with `uv`:

```bash
cd ~/GitHub/deriva-ml-apps && uv sync
uv run deriva-ml-apps serve --backend dev.example.org
```

Or start via MCP: `start_app(app_id="app-launcher", hostname="dev.example.org", catalog_id="1")`

## Quick Start: Minimal HTML App

The simplest app is a single HTML file:

```html
<!DOCTYPE html>
<html>
<head><title>My Data Viewer</title></head>
<body>
  <h1>Dataset Summary</h1>
  <div id="content">Loading...</div>
  <script>
    // The proxy forwards /ermrest/* to the Deriva backend
    // Read catalog/host from URL hash params
    const params = new URLSearchParams(location.hash.slice(1));
    const catalog = params.get('catalog') || '1';

    fetch(`/ermrest/catalog/${catalog}/entity/isa:Dataset`)
      .then(r => r.json())
      .then(data => {
        document.getElementById('content').innerHTML =
          `<p>Found ${data.length} datasets</p>`;
      });
  </script>
</body>
</html>
```

Save to a directory, then register:

```
POST /api/registry
{
  "id": "my-viewer",
  "name": "My Data Viewer",
  "description": "Custom dataset summary",
  "path": "/absolute/path/to/app/directory"
}
```

The app is now available at `http://localhost:8080/apps/my-viewer/`.

## Creating a React App

For richer applications, use Vite + React:

```bash
mkdir -p ~/my-app && cd ~/my-app
pnpm create vite . --template react-ts
pnpm install
pnpm add lucide-react tailwindcss
```

Build and register:

```bash
pnpm build
# Register via API or MCP
```

## Accessing Catalog Data

Apps access the Deriva catalog through the proxy. The server forwards these paths:
- `/ermrest/*` — Catalog API (queries, schema)
- `/authn/*` — Authentication
- `/chaise/*` — Chaise UI resources

**Getting catalog context from URL:** The app-launcher passes catalog info via URL hash:
```
/apps/my-app/#host=dev.example.org&catalog=1
```

Parse this in your app:
```javascript
const params = new URLSearchParams(location.hash.slice(1));
const host = params.get('host');
const catalog = params.get('catalog');
```

## Registering and Managing Apps

### Via MCP Tools

```
# List all registered apps
list_apps()

# Start the app server (starts all apps)
start_app(app_id="schema-workbench", hostname="dev.example.org", catalog_id="1")
```

### Via Registry API

```
# List apps
GET /api/registry

# Register a new app
POST /api/registry
{"id": "my-viz", "name": "My Visualization", "description": "...", "path": "/abs/path"}

# Unregister a dynamic app
DELETE /api/registry/my-viz
```

### Dynamic App Persistence

Dynamic app registrations persist to `~/.deriva-ml/apps/registry.json`. They survive server restarts. Built-in apps (from `apps.json`) cannot be unregistered.

## Claude-Generated Apps

Claude can create custom visualizations on the fly:

1. **Claude writes the app** — HTML/React in a temp directory
2. **Claude builds it** — `pnpm build` for React apps, or just raw HTML
3. **Claude registers it** — `POST /api/registry` with the built directory path
4. **User opens it** — appears in the app-launcher grid at `/`

### Example Workflow

User: "Create a chart showing the diagnosis distribution in my dataset"

1. Create a directory: `~/.deriva-ml/apps/diagnosis-chart/`
2. Write an `index.html` with Chart.js that fetches from `/ermrest/...`
3. Register: `POST /api/registry {"id": "diagnosis-chart", ...}`
4. Open: `http://localhost:8080/apps/diagnosis-chart/#catalog=1`

## App Design Guidelines

- **Use the proxy** — never hardcode Deriva server URLs. Use relative paths (`/ermrest/...`)
- **Read catalog context from hash** — `location.hash` contains host and catalog ID
- **Keep apps self-contained** — one directory with `index.html` + assets
- **For React apps** — build to `dist/`, register the `dist/` directory
- **For quick visualizations** — single HTML file with inline JS is fine

## Related Skills

- **`browse-erd`** — launches the Schema Workbench (a built-in app)
- **`manage-deriva-storage`** *(this plugin)* — uses the Storage Manager (a built-in app); install `deriva-ml-skills` for this skill
- **`/deriva:query-catalog-data`** *(deriva-skills)* — for querying data to display in the app

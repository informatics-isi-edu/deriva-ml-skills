# The Open Knowledge Format (OKF), as used by DerivaML design docs

This is a local summary of the parts of OKF that DerivaML's `docs/design/`
bundle relies on. It exists so the plugin is **self-contained** — if the
upstream spec URL moves or disappears, the contract the design docs depend on is
still recorded here. The authoritative source is the upstream spec:
<https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>.

The `design-experiment` SKILL.md carries the load-bearing rules an author needs
at write-time (the frontmatter contract, the never-add-`resource` rule, the
relationship-verb set). This reference carries the *why* and the mechanics —
read it when you want the background, not on every authoring pass.

## What OKF is

OKF is a deliberately minimal convention for a **self-describing corpus of
knowledge**: Markdown files with a small YAML frontmatter contract, organized as
a directory-tree "bundle". Its design ethos: *"if you can `cat` a file you can
read OKF; if you can `git clone` a repo you can ship it."* No schema registry, no
special tooling. It standardizes only the small set of structural conventions
needed to make a corpus self-describing — it does **not** prescribe a domain
taxonomy or replace domain-specific schemas.

DerivaML adopts OKF for its design docs so the `docs/design/` tree is a
navigable, tool-readable knowledge graph of the project's intent — not a pile of
isolated Markdown files.

## The frontmatter contract

Each concept document opens with a YAML frontmatter block:

- **`type`** — REQUIRED. A short string identifying the kind of concept;
  consumers use it for routing/filtering. Values are not centrally registered;
  consumers MUST tolerate unknown types. DerivaML uses: `Dataset Design`,
  `Experiment Design`, `Feature Design`, `Model Design`, and `Index` (for the
  bundle root).
- **Recommended:** `title`, `description`, `resource`, `tags`, `timestamp`.
- **Extra keys are allowed.** DerivaML adds `status` (the lifecycle ladder
  Draft→Approved→Built→Validated[→Released]) and `slug` (the kebab id) as
  extension keys. This is spec-legal.

### Why DerivaML omits `resource`

OKF's `resource` is *"a URI that uniquely identifies the underlying asset the
concept describes,"* and the spec says it is *"absent for concepts that describe
abstract ideas rather than physical resources."*

A DerivaML design doc is a **specification of intent** — it describes an entity
the project plans to build, authored before that entity exists, and it continues
to describe the *intent* even after the entity is built. That is an abstract
idea, not a physical resource. So `resource` is omitted on every design doc, at
every status. The produced catalog entity (its RID + version) is the concrete
artifact — and that linkage lives in the doc's prose "Status & links" section and
in `tacit-knowledge.md`, not in OKF frontmatter. This draws a clean line:

| Side | Artifact | Nature |
|---|---|---|
| Spec (before) | `docs/design/<entity>/<slug>.md` | abstract — intent, requirements, success criteria |
| Journal (during/after) | `tacit-knowledge.md` | concrete — what happened, decisions, RIDs |
| Catalog (the thing) | the entity at its RID | concrete — the physical resource |

## The bundle and `index.md`

A bundle is a directory tree of Markdown files; OKF defines **no manifest
file**. Two filenames are reserved: **`index.md`** (a directory listing for
navigation) and `log.md` (update history — DerivaML does NOT use this;
`tacit-knowledge.md` is already the project's journal). `docs/design/index.md` is
the bundle root: it carries `type: Index` frontmatter and lists each design doc
as a link, and it states (the primary declaration site) that the corpus follows
OKF.

Conventional body headings OKF suggests "when applicable": `# Schema`,
`# Examples`, `# Citations`. DerivaML uses `## Examples` for the worked example;
it does **not** adopt `# Schema` (that's for an asset's columns, not a spec).

## Links between documents (the connected-corpus payoff)

This is where OKF earns its keep for design docs: a bundle is a **graph**, and
links between concept documents are its edges.

- **A link asserts a relationship; the link itself is UNTYPED.** Per the spec:
  *"A link from concept A to concept B asserts a relationship. The specific kind
  of relationship (parent/child, references, joins-with, depends-on, etc.) is
  conveyed by the surrounding prose, not by the link itself."* There is no
  `related`/`links`/`references` frontmatter field — relationships are ordinary
  Markdown links in the body.
- **Link form.** Two valid forms: **bundle-absolute** (`/dataset/foo.md`, a path
  from the bundle root, leading slash) — *recommended*, because it survives a doc
  moving between subdirectories; and **relative** (`../dataset/foo.md`). DerivaML
  prefers bundle-absolute.
- **Broken links are tolerated.** Per the spec: *"Consumers MUST tolerate broken
  links — a link whose target does not exist in the bundle is not malformed; it
  may simply represent not-yet-written knowledge."* This is why a design may link
  a sibling design that is still `Draft` or not yet authored, and why
  `validate-project-setup` must not flag a dangling design link.

### DerivaML relationship-verb vocabulary

OKF leaves the relationship type to prose. DerivaML standardizes a small,
greppable verb set so the edge types can be inferred uniformly across the corpus.
Each verb goes in the prose immediately beside the link.

| Verb | Edge | Authored in |
|---|---|---|
| **consumes** | experiment / model → dataset | experiment, model |
| **runs** | experiment → model | experiment |
| **produced by** | output-feature → its producing model (the feature-design is the author, pointing back at its model) | feature (output role) |
| **trains on** | model → input feature | model |
| **composed of** | experiment → sub-experiment(s) | experiment (compound) |
| **extends** | model → prior model (checkpoint lineage) | model |
| **precondition on members** | dataset → element-feature — a *data-property* reference, NOT a build dependency | dataset |

### Keeping the graph acyclic

The dependency graph must stay a DAG. Two rules the templates already encode keep
it acyclic:

- **Feature input vs output roles.** An *input* feature (labels a model trains
  on) has no upstream design — the consuming model-design names it (`trains on`),
  not the reverse. An *output*/prediction feature names its producing model
  (`produced by`); the model-design records that feature as an output but does
  NOT list it as one of its own upstream dependencies. The model points down to
  its output feature; the output feature points up to its model; nothing points
  back.
- **Compound experiments.** An experiment composed of sibling experiments links
  them with `composed of` — but only experiments authored *earlier*, so the
  experiment→experiment edges can't form a cycle. A compound experiment is still
  a single `Experiment Design` doc (no new `type`) whose "Upstream designs" simply
  links all the datasets, models, and sub-experiments it composes.

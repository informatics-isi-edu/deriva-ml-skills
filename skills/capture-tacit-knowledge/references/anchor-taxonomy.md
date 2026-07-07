# Anchor Taxonomy — what a tacit-knowledge entry can be *about*

An entry's **anchor** names its referent — the thing the knowledge is about — and is
what retrieval matches on when a teammate later touches that thing. Tacit knowledge is
**not** limited to catalog objects. An anchor can be any of the following, in three
families. The anchor is what goes in the title parenthetical (entry-format.md) and in
the derived index's `anchor` column (index-and-retrieval.md). One entry may carry
several anchors (an instance *and* its type *and* the process that produced it).

## Family A — catalog artifacts (a spectrum of specificity)

1. **Instance** — a specific **RID** (`dataset 7KE`), rendered `ml.cite(rid)`,
   snapshot-pinned. What happened to *this one*.
2. **Class of object** — a **type/name**: a `Dataset_Type` / `Workflow_Type` /
   `Asset_Type` term, a named feature, a model class. A *reusable rule about a kind*
   ("patient-split datasets must avoid cross-split leakage"). Anchor = the type term
   (rendered via `ml.cite` on the term's RID when it has one).
3. **General object** — one of the **five abstractions** (`Dataset`, `Feature`,
   `Model`, `Workflow`, `Execution`) when nothing narrower fits.
4. **Schema entity** — a **table, column, or CV type** (knowledge about the
   *structure*, not the data — "the `Confidence` column is dual-purpose: GT vs
   prediction"). Formally a *class* anchor pointed at a schema entity.

## Family B — process / activity (the thing a *skill* covers)

5. **A process** — "creating a dataset," "training a model," "splitting a dataset,"
   "running a sweep" — knowledge about *how the work is done*, not about an object.
   **Anchor = the skill that owns the process** (`dataset-lifecycle`, `create-feature`,
   `execution-lifecycle`, …). The plugin's skill set is itself a controlled vocabulary
   of processes, so a process anchor is as stable and enumerable as a catalog CV term.
   Write the anchor as the bare skill name (no `ml.cite`; it is not a catalog RID).

## Family C — the socio-technical layer (no catalog handle at all)

6. **Social / team facts** — group dynamics, team structure, expertise, ownership, how
   decisions get made ("the pathologist owns the QC criteria"; "label disputes go to
   consensus"). Knowledge about the *collaboration around* the boundary object.

   > **Privacy constraint (Family C).** Social/team facts often name *individuals* and
   > are written to a **git-tracked, mergeable, team-shared** file — so unlike catalog
   > facts they carry a consent/dignity concern. **Rule:** record **role- and
   > process-level** facts ("QC criteria are owned by the pathology reviewer"; "label
   > disputes go to consensus"), not **evaluative or sensitive claims about a named
   > person** ("X doesn't understand the pipeline"; performance judgments). Prefer the
   > role to the name where the role carries the knowledge; a name is warranted only
   > when the person *is* the durable fact (e.g. a designated owner) and the statement
   > is neutral. When in doubt, capture the convention, not the person. This mirrors
   > the Log's "not a status board / not a snapshot of mutable state" discipline,
   > extended to people.

7. **Domain concepts** — target-domain understanding (staining variance, cohort skew,
   clinical conventions). This is the **domain-background content**; a domain-concept
   entry anchors to a subject in the **`docs/domain/`** bundle (a `type: Concept` doc).
   Per-term meaning that *does* have a catalog home (a vocab term's description) is
   linked by RID, not restated (the "link, don't replicate the catalog" rule).

## Why the non-instance anchors are often the more valuable knowledge

A rule about a *class*, a *process*, a *team fact*, or a *domain concept* applies to the
*next* thing a teammate does; an instance fact may not generalize. Reusable,
cross-time, cross-discipline knowledge is exactly what the system exists to preserve —
so when an entry could anchor at several levels, record the higher-level anchors too,
not only the instance RID.

## Every anchor is a stable, enumerable handle — never free text

- Family A handles are catalog CV terms / RIDs.
- Family B handles are skill names (the plugin's process vocabulary).
- Family C handles are `docs/domain/` subjects (domain) or short role/convention
  phrases (social) — the topic CV (`docs/tacit-knowledge/topics.md`) enumerates the
  recurring ones so they stay consistent.

This is what lets retrieval do a **generalization walk** (index-and-retrieval.md):
match the instance, then widen to its type, its abstraction, the owning process, and
the surrounding social/domain context, merging the hits.

# Citation links for RIDs

Detail for the rule "Always render a RID as a click-through link" in
`/deriva-ml:explore-results`. The rule: anywhere a RID appears in Markdown — chat output and any
document you write (design docs, `tacit-knowledge.md`, READMEs, `Experiments.md`,
PR descriptions) — render it as `[label](cite-url)`, never as a bare string.

## The URL form

The citation URL uses the `/id/` resolver: `https://{host}/id/{catalog}/{rid}[@snaptime]`.

| Entity | Form | Lands on |
|---|---|---|
| Dataset at a **released** version | snapshot-pinned (`…@{snaptime}`) | the dataset as it was at that release |
| Dataset at a **dev** version (PEP 440 `is_devrelease`, e.g. `0.4.0.post1.dev3`) | live (no snaptime) | the current catalog state |
| Asset, Execution, Workflow, Feature | live (no snaptime) | the current record — these aren't versioned like datasets |

## Where the URL comes from

- **Chat output from a bundle resource** — use the row's `cite_url` field. The
  bundle resources (`DatasetDetail`, `ExecutionInputDatasetRef`,
  `ExecutionAssetRef`, …) carry one per row.
- **Writing into a document** (you have `ml = DerivaML(...)` in scope) — call
  `ml.cite(rid)`. It returns the permanent `/id/` URL, snapshot-pinned by default;
  `ml.cite(rid, current=True)` gives the live form.

## Example

`[8N4](https://localhost/id/1407/8N4) cifar10_cnn_weights.pt`, not
`8N4 cifar10_cnn_weights.pt`. Same for a design doc's "Outcome" execution RID, a
`tacit-knowledge.md` entry's catalog handle, or an `Experiments.md` row.

## Citation URL vs resource URI

The citation URL is for a **human** to click. The `deriva://catalog/…` resource
URI is for **programmatic** MCP fetches against the live catalog. Use the
citation URL whenever the audience is a reader.

## When no URL is available

If there is no `cite_url` (a best-effort failure, a thinly built ref) and
`ml.cite()` can't resolve the RID, fall back to the bare RID and **say the link
is missing** — never construct or guess a URL.

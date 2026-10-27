# Confirm authentication before the first catalog operation

Before the **first catalog operation** against a catalog in a session — any read
or write — confirm you're actually authenticated to *that* catalog, so you learn
up-front rather than hitting a blanket-401 mid-operation (a confusing failure deep
in a run). **The check differs by surface — each verifies the credential of the
thing that will actually do the work:**

**Python surface** (scripts, loaders, executions — the local environment holds the
credential). Call `ml.is_authenticated()` on the `DerivaML` instance:

```python
ml = DerivaML(hostname=..., catalog_id=...)
if not ml.is_authenticated():        # one network call: GET /authn/session
    raise SystemExit(
        "Not authenticated to <host>. Log in first:\n"
        "  deriva-globus-auth-utils login --host <host>"
    )
# ml.whoami() returns the identity dict (id, display_name, email, …), or None.
```

**MCP surface** (the MCP server holds the per-request credential, not your local
machine). Before the first MCP catalog op, call the
`deriva_ml_check_authentication(hostname, catalog_id)` tool — it returns
`{"authenticated": bool, "identity": {...}|null}` by asking the server's
`whoami` for *that* catalog. `authenticated: false` means "reached the server, no
valid session"; a connection/DNS/TLS failure comes back as `{"error": ...}` instead
(distinct from "not logged in"). `/deriva-ml:using-deriva-mcp` runs this as part of
the cold-start.

Both share the same caveats:
- **deriva-ml ≥ 1.54** (`is_authenticated`/`whoami`) and the
  `deriva_ml_check_authentication` MCP tool. Do **not** pass a `check_auth=` kwarg
  to `DerivaML(...)` — that is not a constructor parameter and will `TypeError`;
  the Python check is the explicit `is_authenticated()` call after construction.
- They confirm **authentication** (the server knows who you are), not
  **authorization** — a write to a read-only table can still be ACL-refused with a
  valid session. A `True` result means "logged in," not "every operation will pass."
- This section is the canonical statement. Instances point here: the execution /
  loader templates and the `execution-lifecycle` / `setup-ml-catalog` pre-flight
  steps do the Python guard; `using-deriva-mcp` does the MCP pre-flight.

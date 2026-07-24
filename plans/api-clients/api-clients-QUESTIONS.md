# API Clients — Questions

All clarifying questions were resolved during the collaborative design session. See the plan for decisions made:

- **Client interface:** Bespoke per API (not a common interface). Normalization deferred to the ML pipeline phase.
- **Pagination:** Auto-pagination with a `max_pages` safety param.
- **Package manager:** `uv` with `pyproject.toml`.

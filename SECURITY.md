# Security and data handling

Workflow payloads may contain identifiers or user-supplied content. Store only the minimum continuation data required, keep the SQLite file outside Git, restrict filesystem access, and define an expiration or cleanup policy appropriate to the application.

The library does not encrypt payloads, authenticate callers, or decide whether an incoming event belongs to a session. Those controls belong to the host application.

Use synthetic IDs and payloads in public defect reports.

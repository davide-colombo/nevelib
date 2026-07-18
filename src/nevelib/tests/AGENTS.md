# Test guidance

Use minimal synthetic, deterministic fixtures and invariants that fail before a
regression fix. Cover identifier preservation, schemas, and coordinate boundaries.
Isolate external-tool tests or skip them clearly when prerequisites are unavailable.
Use test-managed temporary directories only; never write source or authoritative
output locations, and never use production datasets.

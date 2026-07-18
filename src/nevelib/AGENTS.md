# Source-package guidance

Preserve importable APIs and command-facing data contracts. Keep sequence IDs,
coordinate bases/end semantics, strand handling, and deterministic cluster ordering
stable. Parsers and serializers must reject malformed required input while retaining
documented valid-empty behavior. External-tool wrappers must surface failures rather
than silently reinterpret them. Make the smallest compatible change; do not add or
change dependencies or formats without explicit authorization and regression proof.

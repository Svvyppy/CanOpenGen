# Testing

The project uses pytest for unit, integration, fixture, and golden-output tests. Ruff
checks formatting and lint rules, mypy checks static types, and Doxygen warnings fail
the documentation build. Integration coverage will execute the real bundled Eds2Od.

Phase 1 unit tests cover primitives, all four category partitions, variables, records,
arrays, manual index/subindex parsing, aliases, enums, module namespace identity,
parameter plumbing, TPDO/RPDO mappings, malformed YAML, unsupported versions, JSON
Schema synchronization, ordering normalization, and CLI exit behavior.

Local commands are listed in the repository README. CI runs the same checks on
supported Python versions.

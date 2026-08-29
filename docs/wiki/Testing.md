# Testing

The project uses pytest for unit, integration, fixture, and golden-output tests. Ruff
checks formatting and lint rules, mypy checks static types, and Doxygen warnings fail
the documentation build. Integration coverage will execute the real bundled Eds2Od.

Phase 1 unit tests cover primitives, all four category partitions, variables, records,
arrays, manual index/subindex parsing, aliases, enums, module namespace identity,
parameter plumbing, TPDO/RPDO mappings, malformed YAML, unsupported versions, JSON
Schema synchronization, ordering normalization, and CLI exit behavior.

Phase 2 locks CRC32 compatibility vectors and covers every category range, explicit
priority, automatic allocation, fixed hash collisions, linear probing, wraparound,
range exhaustion, invalid/colliding manual addresses, YAML-order independence,
reproducibility, record subindex reservation/collision/exhaustion, array sequential
subindices and limits, address diagnostics, and a golden Object Dictionary map.

Local commands are listed in the repository README. CI runs the same checks on
supported Python versions.

# Testing

The project uses pytest for unit, integration, fixture, and golden-output tests. Ruff
checks formatting and lint rules, mypy checks static types, and Doxygen warnings fail
the documentation build. Integration coverage executes the real bundled Eds2Od in CI.

Phase 1 unit tests cover primitives, all four category partitions, variables, records,
arrays, manual index/subindex parsing, aliases, enums, module namespace identity,
parameter plumbing, TPDO/RPDO mappings, malformed YAML, unsupported versions, JSON
Schema synchronization, ordering normalization, and CLI exit behavior.

Phase 2 locks CRC32 compatibility vectors and covers every category range, explicit
priority, automatic allocation, fixed hash collisions, linear probing, wraparound,
range exhaustion, invalid/colliding manual addresses, YAML-order independence,
reproducibility, record subindex reservation/collision/exhaustion, array sequential
subindices and limits, address diagnostics, and a golden Object Dictionary map.

Phase 3 covers primitive references, aliases, nested aliases, numerically ordered
enums, enum bases through aliases, enum inheritance, complete cycle diagnostics,
unknown bases/references, exact signed and unsigned range boundaries, invalid enum
storage primitives, reserved type names, and record/array child type lowering. The OD
map golden verifies resolved primitive plus custom type display.

Phase 4 covers direct and nested module loading, filename namespaces, equal transitive
deduplication, direct duplicate rejection, scalar parameter retention/conflicts,
missing modules, complete dependency cycles, same object keys in different modules,
local-first lookup, imported and qualified custom types, qualified PDO references, and
ambiguous reference diagnostics. The OD map golden now includes imported objects.

Phase 5 locks the complete reference EDS as a golden file, checks CiA 306 primitive
codes plus variable/record/array lowering, verifies CLI artifact placement and runner
failure diagnostics, and executes the actual bundled Eds2Od against the generated
`PressureSensor.eds`. The dedicated CI job installs .NET SDK 10, initializes the tool
submodule, generates the example, and runs that acceptance test.

Local commands are listed in the repository README. CI runs the same checks on
supported Python versions.

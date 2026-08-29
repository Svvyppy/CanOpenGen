# CLI Reference

## Validation

```bash
canopengen validate Device/PressureSensor.yml
canopengen validate-all
canopengen validate-all --project-root path/to/project
```

`validate` parses one Device or Module file. `validate-all` discovers
`Modules/*.yml` followed by `Device/*.yml`. Both return non-zero for malformed YAML,
unsupported schema versions, JSON Schema violations, unknown/cyclic custom types,
invalid enum values, missing/duplicate/cyclic modules, conflicting module parameters,
unknown/ambiguous references, invalid manual addresses, collisions, or address-space
exhaustion. A Device resolves its complete import closure; an individual Module resolves
its own transitive dependencies from the surrounding `Modules/` directory.

## Address map

```bash
canopengen map Device/PressureSensor.yml
```

The map groups final indexes by category and displays record/array subindices, resolved
primitive storage, applicable custom type names, access, explicit/automatic provenance,
and non-zero probe distances. The allocation context contains device-local objects and
every resolved transitive module object.

## Address diagnostics

```bash
canopengen address PressureSensor.pressure --category telemetry
canopengen address PressureSensor.pressure --category telemetry \
  --config Device/PressureSensor.yml
```

Without a configuration, output shows the canonical hash key, CRC32, range, initial
slot, and initial index. Complete context additionally loads the module closure and
shows the final index, allocation source, and probe distance.

## Generation

```bash
canopengen generate Device/PressureSensor.yml --output build/canopen
```

Generation loads the complete device/module graph, resolves types and references,
allocates addresses, writes `<device>.eds`, and invokes the bundled CANoopEn Eds2Od to
write `<device>Od.hpp` and `<device>Od.cpp`. All artifacts stay in `--output`.

The default runner first uses a bundled native Eds2Od binary when available, otherwise
the bundled .NET project. Set `CANOPENGEN_EDS2OD` or pass `--eds2od path/to/Eds2Od` to
select an explicit executable. Tool failures include the captured output and return a
non-zero command result.

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
invalid enum values, invalid manual addresses, collisions, or address-space exhaustion.
Until module resolution is implemented, each definition's local types and objects are
resolved independently.

## Address map

```bash
canopengen map Device/PressureSensor.yml
```

The map groups final indexes by category and displays record/array subindices, resolved
primitive storage, applicable custom type names, access, explicit/automatic provenance,
and non-zero probe distances. Imported module objects are explicitly omitted until
Phase 4.

## Address diagnostics

```bash
canopengen address PressureSensor.pressure --category telemetry
canopengen address PressureSensor.pressure --category telemetry \
  --config Device/PressureSensor.yml
```

Without a configuration, output shows the canonical hash key, CRC32, range, initial
slot, and initial index. Complete context additionally shows the final index,
allocation source, and probe distance.

## Reserved command

`generate` remains registered but fails with a diagnostic naming the Phase 5
EDS/Eds2Od implementation boundary. It does not produce placeholder artifacts.

# CLI Reference

## Available in Phase 1

```bash
canopengen validate Device/PressureSensor.yml
canopengen validate-all
canopengen validate-all --project-root path/to/project
```

`validate` parses one Device or Module file. `validate-all` discovers
`Modules/*.yml` followed by `Device/*.yml`. Both return non-zero for malformed YAML,
unsupported schema versions, or JSON Schema violations. Output explicitly labels this
as structural validation until semantic resolver stages are added.

## Reserved command shape

`generate`, `map`, and `address` are registered so their public argument shape can grow
incrementally, but currently fail with a diagnostic naming the implementation phase.
They do not produce placeholder artifacts or invented address results.

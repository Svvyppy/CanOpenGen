# YAML Reference

Every definition uses `schema: 1` and contains exactly one `device` or `module` block.
Unknown fields are rejected. The canonical IDE schema is
`schemas/canopengen.schema.json` and is validated by the same parser used by the CLI.

## Top-level fields

| Field | Meaning |
| --- | --- |
| `schema` | Required public schema version; currently exactly `1` |
| `device` | Device `name` and optional plain-string `info` |
| `module` | Module display `name` and optional plain-string `info` |
| `modules` | Simple or parameterized module imports |
| `types` | Alias and enum declarations |
| `objects` | Application Object Dictionary declarations |
| `pdo` | Symbolic `tpdo` and `rpdo` mappings |

Module imports accept either a name or scalar parameter assignments:

```yaml
modules:
  - CommonTypes
  - name: Diagnostics
    params:
      channel_count: 4
```

Custom types require a `base`. An optional `enum` maps symbolic names to integers:

```yaml
types:
  Pressure:
    base: uint32
  DeviceState:
    base: uint8
    enum:
      INIT: 0
      READY: 1
```

## Objects

Every object requires `category` and `type`. Variables and arrays require `access`;
record containers derive access from their fields. Optional explicit `index` values are
integers, so hexadecimal YAML values such as `0x2200` are accepted.

Categories are `telemetry`, `command`, `configuration`, and `diagnostic`. Access modes
are `ro`, `wo`, and `rw`.

Records require one or more `fields`. Every field has `type` and `access`, with optional
`info` and an explicit `subindex` from 1 through 254. Arrays require `item_type`,
`length` from 1 through 255, and `access`.

## PDO mappings

PDO groups contain named mappings whose entry order is significant:

```yaml
pdo:
  tpdo:
    sensor_data:
      mapping:
        - pressure
        - state
```

Phase 1 validates this structure but deliberately defers reference/type/payload
validation to the PDO phase.

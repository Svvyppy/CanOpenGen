# Object Dictionary Allocation

Application objects use deterministic unsigned IEEE CRC-32 allocation:

| Category | Inclusive range | Slots |
| --- | --- | --- |
| `telemetry` | `0x2000–0x27FF` | 2048 |
| `command` | `0x2800–0x2FFF` | 2048 |
| `configuration` | `0x3000–0x37FF` | 2048 |
| `diagnostic` | `0x3800–0x3FFF` | 2048 |

For each category, CanOpenGen validates and reserves every explicit index, sorts all
automatic objects lexically by qualified name, then hashes this exact UTF-8 key:

```text
<category>:<qualified-name>
```

The reference operation is:

```python
crc = zlib.crc32(canonical_key.encode("utf-8")) & 0xFFFFFFFF
initial_slot = crc % 2048
index = range_start + initial_slot
```

If the slot is occupied, allocation checks the next slot, wraps at the end of the
category, and stops at the first free index. It fails only after every slot has been
checked.

## Compatibility vector

```text
Qualified name:       PressureSensor.pressure
Canonical key:        telemetry:PressureSensor.pressure
CRC32:                0xA66C98DF
Initial slot:         223
Initial index:        0x20DF
```

The example declares an explicit `0x2200`, so complete-context diagnostics show
`0x20DF` as the hash result and `0x2200` as the final index.

## Stability

No persistent address lock file is used. Equivalent complete configurations reproduce
the same Object Dictionary regardless of YAML mapping order. Adding, removing, or
renaming an object may alter addresses in a collision/probe chain. Use explicit
addresses for interfaces that require stability across configuration changes.

`canopengen address` displays the canonical key and initial calculation. Supplying
`--config` also displays the final explicit or post-probing result.

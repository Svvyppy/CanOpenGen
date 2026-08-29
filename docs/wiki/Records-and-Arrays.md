# Records and Arrays

Records reserve subindex `0x00` for the read-only entry count. Explicit field
subindices from `0x01` through `0xFE` are reserved first. Remaining fields are sorted
by qualified name and allocated with CRC32 plus wraparound linear probing over exactly
254 slots. The field key is its qualified name without a category prefix:

```text
PressureSensor.calibration.offset
```

Arrays also reserve `0x00` for the count, then always use standard sequential CANopen
semantics:

```text
0x01 element 1
0x02 element 2
...
```

Array elements are never hashed. Schema v1 supports lengths from 1 through 255.

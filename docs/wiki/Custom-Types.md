# Custom Types

Schema version 1 supports aliases, nested aliases, and integer-backed enums. Every
custom type must ultimately lower to a standard CANopen primitive.

## Aliases

```yaml
types:
  RawPressure:
    base: uint32
  Pressure:
    base: RawPressure
```

The resolved chain is `Pressure -> RawPressure -> uint32`. Resolution is recursive and
independent of YAML declaration order. A cycle fails with the complete dependency
chain, for example `A -> B -> C -> A`. Unknown bases and object/field/array references
identify the source file and affected semantic name.

Custom declarations cannot shadow primitive aliases or the structural names `record`
and `array`.

## Enums

```yaml
types:
  StateStorage:
    base: uint8
  DeviceState:
    base: StateStorage
    enum:
      INIT: 0
      READY: 1
      ERROR: 3
```

An enum base may itself be a nested alias, but it must ultimately reach `int8`,
`int16`, `int32`, `int64`, or the corresponding unsigned primitive. Every value is
checked against the exact resolved range. Aliases of an enum inherit its symbolic
semantics.

EDS and CANopen storage use the resolved primitive. Documentation retains both the
custom type name and numerically ordered enum members.

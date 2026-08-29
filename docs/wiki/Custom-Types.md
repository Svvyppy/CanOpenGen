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

## Module lookup

Within a Device or Module, local custom types take precedence. If no local declaration
matches, CanOpenGen searches the owner's transitive imports. Exactly one imported match
is accepted; multiple matches require an explicit qualified type:

```yaml
objects:
  firmware_version:
    category: diagnostic
    type: CommonTypes.FirmwareVersion
    access: ro
```

Aliases may also use qualified bases. Imported aliases and enums retain the same
lowering, cycle, and range validation behavior as local declarations.

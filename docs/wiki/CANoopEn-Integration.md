# CANoopEn and Eds2Od Integration

CanOpenGen generates a CiA 306 EDS and then invokes the bundled
[CANoopEnTools](https://github.com/xyntos-ch/CANoopEnTools) `Eds2Od` submodule. Direct
C++ generation is deliberately outside the MVP.

## Eds2Od contract

The inspected tool reads only `[INDEX]` and `[INDEXsubN]` sections. A leaf entry must
contain `DataType`; the supported access spellings are `const`, `ro`, `wo`, `rw`, `rwr`,
and `rww`. Container sections without `DataType` provide their `ParameterName`; every
record/array leaf is represented by a subindex section.

CanOpenGen uses CiA 306 type codes supported by the tool, including `0x0002`–`0x0004`
for signed 8/16/32-bit integers, `0x0005`–`0x0007` for unsigned 8/16/32-bit integers,
`0x0015`/`0x001B` for 64-bit integers, `0x0008`/`0x0011` for real values,
`0x0009` for visible strings, and `0x000F` for domains. Custom aliases and enums are
lowered before EDS generation.

The exact tool invocation is:

```text
Eds2Od <device>.eds <device>Od.cpp <device>Od.hpp
```

`canopengen generate` captures standard output/error, fails on a non-zero tool status,
and verifies that both C++ files were written. CI runs this path for `PressureSensor.yml`
and the real-tool acceptance test. The submodule targets .NET SDK 10 when no native
release binary is supplied.

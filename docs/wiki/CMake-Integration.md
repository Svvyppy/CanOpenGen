# CMake Integration

CanOpenGen is consumed from a firmware project together with a separate
`CanOpenDefinitions` checkout. Production YAML does not belong in either the firmware
source tree or this generator repository.

Set these cache variables in a preset or on the CMake command line:

```json
{
  "cacheVariables": {
    "CANOPEN_GEN_DIR": "${sourceDir}/external/CanOpenGen",
    "CANOPEN_DEFINITIONS_DIR": "${sourceDir}/external/CanOpenDefinitions",
    "CANOPEN_LOCAL_DEVICE": "MainController",
    "CANOPEN_REMOTE_DEVICES": "PressureSensor;MotorController"
  }
}
```

Include the generator module and declare one concise firmware integration after the
firmware target is created:

```cmake
include("${CANOPEN_GEN_DIR}/cmake/CanOpenGen.cmake")

canopen_firmware(
    TARGET main_controller
    LOCAL ${CANOPEN_LOCAL_DEVICE}
    REMOTE ${CANOPEN_REMOTE_DEVICES}
    DEFINITIONS_DIR ${CANOPEN_DEFINITIONS_DIR}
)
```

The function resolves `Device/<name>.yml` and `Modules/` inside `DEFINITIONS_DIR`.
It adds `main_controller_canopen` to the build graph (and as a dependency of the real
target when it exists). By default each device has an isolated directory below
`${CMAKE_CURRENT_BINARY_DIR}/generated/canopen/<DeviceFilenameStem>/`.

`LOCAL` generates the real CANoopEn node Object Dictionary. Every `REMOTE` device is
generated from the same production YAML but its CANoopEn Object Dictionary is wrapped
in a namespace derived strictly from the YAML filename stem, preventing symbol
collisions when several remote dictionaries are linked together. All devices also
receive `<stem>Objects.hpp`, which exposes typed index/subindex metadata and generic
`SetValue`/`GetValue` helpers so firmware code does not need numeric OD addresses.

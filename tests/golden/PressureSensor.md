# PressureSensor

Example CANopen pressure sensor.

## Modules

| Namespace | Module | Parameters | Dependencies | Description |
| --- | --- | --- | --- | --- |
| `CommonTypes` | Common Types | — | — | Shared datatype aliases. |
| `Diagnostics` | Diagnostics | `channel_count=4` | `CommonTypes` | Common runtime diagnostic objects. |
| `FirmwareInfo` | Firmware Information | — | `CommonTypes` | Common firmware identification objects. |

## Object Dictionary

## Telemetry

### `samples`

| Property | Value |
| --- | --- |
| Qualified name | `PressureSensor.samples` |
| Address | `0x20EB:00` |
| Kind | array |
| Resolved type | array of `uint16`, length 8 |
| Access | `ro` |
| Allocation | automatic (CRC32) |

Last eight raw pressure samples.

#### Array elements

| Subindex | Key | Qualified name | Resolved type | Access | Allocation | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `0x01` | `samples[1]` | `PressureSensor.samples[1]` | `uint16` | `ro` | sequential | — |
| `0x02` | `samples[2]` | `PressureSensor.samples[2]` | `uint16` | `ro` | sequential | — |
| `0x03` | `samples[3]` | `PressureSensor.samples[3]` | `uint16` | `ro` | sequential | — |
| `0x04` | `samples[4]` | `PressureSensor.samples[4]` | `uint16` | `ro` | sequential | — |
| `0x05` | `samples[5]` | `PressureSensor.samples[5]` | `uint16` | `ro` | sequential | — |
| `0x06` | `samples[6]` | `PressureSensor.samples[6]` | `uint16` | `ro` | sequential | — |
| `0x07` | `samples[7]` | `PressureSensor.samples[7]` | `uint16` | `ro` | sequential | — |
| `0x08` | `samples[8]` | `PressureSensor.samples[8]` | `uint16` | `ro` | sequential | — |

### `pressure`

| Property | Value |
| --- | --- |
| Qualified name | `PressureSensor.pressure` |
| Address | `0x2200:00` |
| Kind | variable |
| Resolved type | `uint32` (`Pressure`) |
| Access | `ro` |
| Allocation | explicit |

Current measured pressure.

### `state`

| Property | Value |
| --- | --- |
| Qualified name | `PressureSensor.state` |
| Address | `0x24E4:00` |
| Kind | variable |
| Resolved type | `uint8` (`DeviceState`) |
| Access | `ro` |
| Allocation | automatic (CRC32) |

Current device state.

## Commands

### `reset`

| Property | Value |
| --- | --- |
| Qualified name | `PressureSensor.reset` |
| Address | `0x2C31:00` |
| Kind | variable |
| Resolved type | `uint8` |
| Access | `wo` |
| Allocation | automatic (CRC32) |

Reset command.

## Configuration

### `calibration`

| Property | Value |
| --- | --- |
| Qualified name | `PressureSensor.calibration` |
| Address | `0x3129:00` |
| Kind | record |
| Resolved type | record |
| Access | `n/a` |
| Allocation | automatic (CRC32) |

Pressure calibration parameters.

#### Record fields

| Subindex | Key | Qualified name | Resolved type | Access | Allocation | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `0x01` | `offset` | `PressureSensor.calibration.offset` | `int32` | `rw` | explicit | Calibration offset. |
| `0x82` | `scale` | `PressureSensor.calibration.scale` | `float32` | `rw` | automatic (CRC32) | Calibration scale. |

## Diagnostics

### `supply_voltage`

| Property | Value |
| --- | --- |
| Qualified name | `Diagnostics.supply_voltage` |
| Address | `0x3AC1:00` |
| Kind | variable |
| Resolved type | `uint16` |
| Access | `ro` |
| Allocation | automatic (CRC32) |

Device supply voltage.

### `firmware_version`

| Property | Value |
| --- | --- |
| Qualified name | `FirmwareInfo.firmware_version` |
| Address | `0x3DA3:00` |
| Kind | variable |
| Resolved type | `uint32` (`FirmwareVersion`) |
| Access | `ro` |
| Allocation | automatic (CRC32) |

Packed firmware version.

### `error_count`

| Property | Value |
| --- | --- |
| Qualified name | `Diagnostics.error_count` |
| Address | `0x3DF8:00` |
| Kind | variable |
| Resolved type | `uint32` |
| Access | `ro` |
| Allocation | automatic (CRC32) |

Number of errors observed since reset.

## Custom Types

### `CommonTypes.FirmwareVersion`

| Property | Value |
| --- | --- |
| Kind | alias |
| Declared base | `uint32` |
| Resolved primitive | `uint32` |
| Alias chain | `FirmwareVersion` → `uint32` |

### `PressureSensor.DeviceState`

| Property | Value |
| --- | --- |
| Kind | enum |
| Declared base | `uint8` |
| Resolved primitive | `uint8` |
| Alias chain | `DeviceState` → `uint8` |

| Name | Value |
| --- | --- |
| `INIT` | `0` |
| `READY` | `1` |
| `ACTIVE` | `2` |
| `ERROR` | `3` |

### `PressureSensor.Pressure`

| Property | Value |
| --- | --- |
| Kind | alias |
| Declared base | `RawPressure` |
| Resolved primitive | `uint32` |
| Alias chain | `Pressure` → `RawPressure` → `uint32` |

### `PressureSensor.RawPressure`

| Property | Value |
| --- | --- |
| Kind | alias |
| Declared base | `uint32` |
| Resolved primitive | `uint32` |
| Alias chain | `RawPressure` → `uint32` |


## PDO Mapping

### `sensor_data` (TPDO)

Declared scalar payload: 56 bits. PDO encoding and 64-bit validation are handled by the PDO generation phase.

| Declared mapping | Resolved target | Width |
| --- | --- | --- |
| `pressure` | `PressureSensor.pressure` | 32 bits |
| `state` | `PressureSensor.state` | 8 bits |
| `Diagnostics.supply_voltage` | `Diagnostics.supply_voltage` | 16 bits |

### `commands` (RPDO)

Declared scalar payload: 8 bits. PDO encoding and 64-bit validation are handled by the PDO generation phase.

| Declared mapping | Resolved target | Width |
| --- | --- | --- |
| `reset` | `PressureSensor.reset` | 8 bits |

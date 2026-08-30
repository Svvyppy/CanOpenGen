# Device Files

Device files live under `Device/`, declare `schema: 1`, and provide the device
namespace, local definitions, module imports, and PDO mappings. The declared device
name is the namespace for local qualified names:

```text
PressureSensor.pressure
PressureSensor.calibration.offset
```

The checked-in `examples/definitions/Device/PressureSensor.yml` is the schema-v1 reference example. Named
type, object, field, and PDO mappings are normalized lexically by the raw parser so
irrelevant YAML mapping order cannot leak into later allocation behavior. PDO mapping
list order remains significant and is preserved.

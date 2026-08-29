# Getting Started

CanOpenGen currently supports schema-v1 validation, alias/enum lowering, and
deterministic device-local address allocation on Linux with Python 3.11 or newer. From
a checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
canopengen validate Device/PressureSensor.yml
canopengen validate-all
canopengen map Device/PressureSensor.yml
```

`validate` checks YAML structure, all local custom types, and currently available
address semantics. `map` shows resolved primitive/custom type metadata, allocated
device-local objects, and address provenance. Imported modules, cross-namespace
references, and PDO payloads are not resolved yet; those semantic checks arrive in
later phases without changing the schema-v1 command shape.

# Getting Started

CanOpenGen currently supports structural schema-v1 validation on Linux with Python
3.11 or newer. From a checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
canopengen validate Device/PressureSensor.yml
canopengen validate-all
```

`validate` currently proves that YAML syntax and public structure are valid and builds
the raw internal representation. It does not yet resolve imported modules, custom type
bases, references, addresses, or PDO payloads. Those semantic checks arrive in later
phases without changing the schema-v1 command shape.

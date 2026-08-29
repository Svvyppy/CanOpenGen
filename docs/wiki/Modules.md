# Modules

Reusable module definitions live under `Modules/`. Module filenames define their
namespaces; `Modules/FirmwareInfo.yml` always owns names such as
`FirmwareInfo.firmware_version`, even when its display name is “Firmware Information”.

## Loading and dependencies

Both Device and Module definitions may import modules:

```yaml
modules:
  - CommonTypes
  - FirmwareInfo
```

CanOpenGen recursively loads `Modules/<name>.yml`. The resolved tuple is deterministic
and dependency-first. An equal module reached through multiple transitive paths is
included once, while a duplicate in one `modules` list is an authoring error. Missing
modules and cycles fail contextually; cycles include the complete chain such as
`A -> B -> C -> A`.

## Parameters

Scalar configurations use the schema-v1 extension point:

```yaml
modules:
  - name: Diagnostics
    params:
      channel_count: 4
```

Assignments are retained immutably on `ResolvedModule`. If a diamond reaches the same
namespace with different assignments, resolution fails rather than choosing one.
Phase 4 deliberately does not add a placeholder or template language.

## Visibility and references

Types and object references resolve against their owner namespace first, then the
transitive imported namespaces. An unqualified imported name must have one match.
Explicit names such as `CommonTypes.FirmwareVersion` and
`Diagnostics.supply_voltage` avoid ambiguity. Consequently, `Alpha.status` and
`Beta.status` coexist safely even though their local YAML keys are equal.

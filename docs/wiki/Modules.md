# Modules

Reusable module definitions live under `Modules/`. Module filenames define their
namespaces; `Modules/FirmwareInfo.yml` always owns names such as
`FirmwareInfo.firmware_version`, even when its display name is “Firmware Information”.

Phase 1 parses simple and scalar-parameterized imports into unresolved `ModuleImport`
models. Recursive loading, deduplication, cycle detection, parameter application, and
reference resolution remain isolated in the module-resolution phase.

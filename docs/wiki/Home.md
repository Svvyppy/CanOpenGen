# CanOpenGen Wiki

CanOpenGen turns a versioned YAML device description and reusable YAML modules into
a validated CANopen Object Dictionary, EDS, developer documentation, and CANoopEn C++
output produced by Eds2Od.

The implementation is currently being built in phases. Pages in this source tree are
the canonical Wiki source and will grow with the corresponding public functionality.

## Contents

- [Getting Started](Getting-Started.md)
- [YAML Reference](YAML-Reference.md)
- [Device Files](Device-Files.md)
- [Modules](Modules.md)
- [Custom Types](Custom-Types.md)
- [Object Dictionary Allocation](Object-Dictionary-Allocation.md)
- [Records and Arrays](Records-and-Arrays.md)
- [PDO Mapping](PDO-Mapping.md)
- [CMake Integration](CMake-Integration.md)
- [CLI Reference](CLI-Reference.md)
- [CANoopEn Integration](CANoopEn-Integration.md)
- [Architecture](Architecture.md)
- [Development Workflow](Development-Workflow.md)
- [Testing](Testing.md)
- [Release Process](Release-Process.md)

## Wiki publishing

Edit Wiki pages only in `docs/wiki` in the main repository. To publish them, clone the
repository's separate GitHub Wiki repository, replace its Markdown pages with the
reviewed contents of this directory, inspect the diff, and commit that synchronized
copy. This keeps repository history as the single authored documentation source.


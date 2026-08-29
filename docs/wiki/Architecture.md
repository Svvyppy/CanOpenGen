# Architecture

CanOpenGen uses explicit stages so YAML parsing, semantic behavior, allocation, and
output formats do not leak into one another:

```text
YAML -> raw models -> module resolver -> type resolver
     -> allocator -> validator -> resolved IR -> generators
```

Generators consume only resolved and validated internal representations. The EDS
backend feeds Eds2Od; it does not produce CANoopEn C++ itself. This page will record
the reviewed internal model after Phase 1.


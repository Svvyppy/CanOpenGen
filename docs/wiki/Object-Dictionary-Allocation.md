# Object Dictionary Allocation

Application objects will use deterministic IEEE CRC-32 allocation with category-based
index ranges and linear probing. Explicit addresses are reserved first. No persistent
address lock file is part of the design.

The exact canonicalization rules and compatibility guarantees will be documented with
the Phase 2 allocator and deterministic test vectors.


# Changelog

All notable changes to CanOpenGen will be documented in this file by the automated
semantic-release workflow.

The project follows [Semantic Versioning](https://semver.org/) and derives releases
from Conventional Commits merged into `main`.

<!-- version list -->

## v1.1.0 (2026-08-30)

### Bug Fixes

- Allow CMake Eds2Od override without submodule
  ([`f57a853`](https://github.com/Svvyppy/CanOpenGen/commit/f57a853517e2bff1c33d7f9d7a49d74e7c0a4526))

- Resolve generated enum symbols by owner scope
  ([`bcd5397`](https://github.com/Svvyppy/CanOpenGen/commit/bcd539742e116ed7398e28f143c9d327e2c9f7e8))

### Chores

- **release**: 1.1.0
  ([`bde2f24`](https://github.com/Svvyppy/CanOpenGen/commit/bde2f24a29d4d84121940f0f852fd3f6c8fa48a8))

### Features

- Support external CANopen definitions
  ([`684c379`](https://github.com/Svvyppy/CanOpenGen/commit/684c37988b058b397a19cd98b6112977c3b76351))

### Testing

- Cover remote Eds2Od regeneration
  ([`204ef40`](https://github.com/Svvyppy/CanOpenGen/commit/204ef40b37b4f7cb8b1595f6ed3c95903fc9426c))


## v1.0.0 (2026-08-29)

### Features

- Complete YAML-to-EDS-to-Eds2Od CANopen Object Dictionary generation pipeline.
- Deterministic allocation, reusable modules, custom aliases/enums, Markdown, PDO
  mapping validation, and CMake build-graph integration.

## v0.1.0 (2026-08-29)

- Initial Release

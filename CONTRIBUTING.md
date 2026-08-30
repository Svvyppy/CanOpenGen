# Contributing to CanOpenGen

Create feature and fix branches from `develop`, and submit focused pull requests back
to `develop`. Create each `release/*` branch from `develop`; after publishing the
release, merge it back into `develop` so the changelog and version stay synchronized.
`main` is not part of this workflow. Direct pushes to permanent branches are discouraged.

Use Conventional Commits such as:

```text
feat(parser): add device object parsing
fix(pdo): reject mappings larger than 64 bits
docs(wiki): document automatic addressing
```

Before opening a pull request, run:

```bash
ruff format --check .
ruff check .
mypy
pytest
cmake -S . -B build
cmake --build build --target docs
```

Every externally visible behavior needs tests and corresponding schema and
documentation updates where relevant. See the
[development workflow](docs/wiki/Development-Workflow.md) for the full policy.

# Testing

The project uses pytest for unit, integration, fixture, and golden-output tests. Ruff
checks formatting and lint rules, mypy checks static types, and Doxygen warnings fail
the documentation build. Integration coverage will execute the real bundled Eds2Od.

Local bootstrap commands are listed in the repository README. CI runs the same checks
on supported Python versions.


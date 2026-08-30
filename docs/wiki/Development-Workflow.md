# Development Workflow

`develop` is the permanent integration branch. Create short-lived `feature/*`, `fix/*`,
`docs/*`, or `ci/*` branches from `develop`, use Conventional Commits, and submit
focused pull requests back to `develop`. Create a `release/*` branch from `develop`
only when publishing a release, then merge that branch back into `develop` after the
release. `main` is not used.

## Definition of done

A change includes its implementation and tests, passes formatting, linting, typing,
unit and relevant integration checks, and updates public schema, examples, and
documentation when behavior changes. Meaningful bug fixes include regression tests
where practical.

## Recommended branch protection

Configure `develop` and the protected `release/*` branch pattern in GitHub with:

- direct pushes disabled;
- pull requests required;
- CI checks required;
- branches required to be up to date before merge.

Repository permissions remain an administrator concern and are not managed by the
CanOpenGen application.

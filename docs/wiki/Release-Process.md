# Release Process

CanOpenGen follows Semantic Versioning. `develop` is the only permanent development
branch; `main` is not used. To publish, create a `release/*` branch from the current
`develop` head. Python Semantic Release analyzes its Conventional Commits to determine
the version, update the changelog, create the tag, and publish the GitHub release.

Before publishing, require the complete MVP acceptance suite, documentation, Doxygen,
CMake, and real Eds2Od pipeline to pass on the release branch. Merge the release branch
back into `develop` after publishing so its version and changelog remain canonical.

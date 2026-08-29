# Release Process

CanOpenGen follows Semantic Versioning. Conventional Commits merged into `main` are
analyzed by Python Semantic Release to determine the version, update the changelog,
create the tag, and publish the GitHub release.

Pre-1.0 releases verify the automation. The project reaches `v1.0.0` only after the
complete MVP acceptance suite, documentation, Doxygen, CMake, and real Eds2Od pipeline
pass on `develop` and the release pull request passes on `main`.


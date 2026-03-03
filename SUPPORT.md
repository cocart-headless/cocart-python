<!-- CoCart SDK Support Policy Template v1 -->

# Support & Versioning Policy

> **Note:** This SDK is currently in development. The full support lifecycle (maintenance phase for previous major versions, EOL (End-of-Life) grace periods) takes effect once the SDK is declared stable and production-ready.

## Versioning

This SDK follows [Semantic Versioning](https://semver.org/) (SemVer):

- **Major** (X.0.0) — Breaking changes to the public API
- **Minor** (x.Y.0) — New features that are backward-compatible
- **Patch** (x.y.Z) — Bug fixes and security patches

Only the **latest major version** receives active development. Older major versions remain available for install but receive no updates. Migration guides are provided in the `docs/` folder for major version upgrades.

### What constitutes a breaking change

- Removing or renaming a public class, method, or function
- Changing required parameters of a public method
- Changing return types of a public method
- Removing a public exception class
- Dropping a Python version from the supported matrix

### What is NOT a breaking change

- Adding new optional parameters to existing methods
- Adding new classes, methods, or response fields
- Internal refactors that do not affect the public API
- Adding a new Python version to the supported matrix
- Bug fixes that correct behavior to match documentation

## SDK Lifecycle

| Phase | Description | Duration |
|---|---|---|
| **Active** | New features, bug fixes, security patches | Current major version |
| **Maintenance** | Security patches and critical bug fixes only | Previous major version, 12 months |
| **Deprecated** | No updates; remains installable | After maintenance ends |

## Supported Python Versions

| Python | Status | SDK Support | Notes |
|---|---|---|---|
| 3.13 | Active | Supported | Tested in CI |
| 3.12 | Active | Supported | Tested in CI |
| 3.11 | Security | Supported | Tested in CI |
| 3.10 | Security | Supported | Tested in CI |
| 3.9 | Security | Minimum version | Tested in CI |
| 3.8 and below | EOL | Not supported | |

### Version support policy

We support all Python versions that are in **active** or **security-fix** status according to the [Python Release Cycle](https://devguide.python.org/versions/).

- **Adding new versions:** When a new Python version is released (typically each October), we add CI testing and official support within 3 months.
- **Dropping old versions:** When a Python version reaches end-of-life, we continue supporting it for **6 months**, then drop it in the next minor or major SDK release.

## Deprecation Notices

We communicate deprecations through:

1. **In-code warnings** — `warnings.warn("...", DeprecationWarning, stacklevel=2)` so users see the warning at the call site
2. **Changelog entry** — Every deprecation is noted in release notes
3. **Minimum one minor release** — A deprecation warning ships at least one minor version before the deprecated feature is removed
4. **Migration guide** — Major version upgrades include a migration guide in the `docs/` folder

## Getting Help

- **Documentation:** https://cocartapi.com/docs
- **Community:** https://cocartapi.com/community
- **Issues:** https://github.com/cocart-headless/cocart-python-sdk/issues

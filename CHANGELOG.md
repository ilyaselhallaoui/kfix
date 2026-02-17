# Changelog

All notable changes to kfix will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Corrected cluster accessibility checks to fail on non-zero `kubectl cluster-info` exit codes
- Added safer auto-fix controls with explicit policy handling
- Hardened local config storage permissions for API keys

### Added
- Service health checks in `kfix scan` (detect services with no ready endpoints)

## [0.2.0] - 2026-02-17

### Added
- **Deployment diagnosis**: New `kfix diagnose deployment` command
- **Service diagnosis**: New `kfix diagnose service` command
- **Comprehensive test suite**: Full unit test coverage for all modules
- **Type hints**: Complete type annotations throughout codebase
- **Google-style docstrings**: Detailed documentation for all functions
- **Code formatting**: Black, isort, and ruff configuration
- **Pre-commit hooks**: Automated code quality checks
- **Makefile**: Convenient commands for development tasks
- **Contributing guide**: Detailed contribution guidelines
- **CI/CD pipeline**: GitHub Actions for testing and releases

### Changed
- Improved error handling across all modules
- Enhanced CLI output formatting
- Better structured code organization
- Updated README with comprehensive examples

### Fixed
- Type checking issues with mypy
- Import sorting consistency
- Code style compliance

## [0.1.0] - 2026-02-15

### Added
- Initial release
- Pod diagnosis with AI-powered analysis
- Node diagnosis capabilities
- Error explanation feature
- Configuration management
- Integration with Anthropic Claude API
- Rich terminal output
- kubectl integration

### Features
- `kfix diagnose pod` - Diagnose pod issues
- `kfix diagnose node` - Diagnose node issues
- `kfix explain` - Explain Kubernetes errors
- `kfix config set` - Configure API key
- `kfix version` - Show version

[Unreleased]: https://github.com/ilyaselhallaoui/kfix/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ilyaselhallaoui/kfix/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ilyaselhallaoui/kfix/releases/tag/v0.1.0

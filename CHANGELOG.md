# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-02-26

### Added
- Django app structure checks (urls.py, views.py, models.py, migrations/, navigation.py, tables.py, filtersets.py, forms.py, template_content.py, graphql.py, api/ directory)
- Security pattern checks (hardcoded secrets, verify=False, request timeouts, permission mixins, .env files, .gitignore coverage)
- Plugin Certification Program readiness checks (OSI license, tests, docs, compatibility matrix, screenshots, CONTRIBUTING guide, PyPI metadata)
- Ruff detection as alternative to black+isort+flake8 in pyproject.toml, workflows, and linting checks
- Additional structure checks (CONTRIBUTING.md, COMPATIBILITY.md, .editorconfig, .pre-commit-config.yaml, docs/ directory)

## [0.1.0] - 2026-02-26

### Added
- Initial release
- Structure checks (pyproject.toml, README, CHANGELOG, LICENSE, .gitignore, workflows, templates)
- PluginConfig validation via AST parsing (name, verbose_name, description, version, author, base_url, min/max_version)
- pyproject.toml validation (build-system, project metadata, URLs, dev extras, tool config)
- Version synchronization checks (__init__.py vs pyproject.toml vs CHANGELOG.md)
- CHANGELOG.md format validation (Keep a Changelog compliance)
- README.md content checks (features, install, configuration, badges)
- GitHub Actions workflow validation (CI lint + release publish)
- Code linting (black, isort, flake8)
- Package build validation (python -m build + twine check)
- Multiple output formats: terminal (color), JSON, markdown
- Docker container support
- CLI with --format, --strict, --skip-lint, --skip-build options

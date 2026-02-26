# netbox-plugin-audit

Audit tool for validating NetBox plugin structure, metadata, and best practices.

Given a git URL (or local path), it clones the repo, runs ~95 checks across 10 categories, and outputs a color-coded report.

## Features

- **Structure checks** — Required files (pyproject.toml, README, CHANGELOG, LICENSE, .gitignore, workflows)
- **PluginConfig validation** — AST parsing of `__init__.py` for all required attributes
- **pyproject.toml validation** — Build system, metadata, URLs, dev deps, tool config
- **Version sync** — Checks `__init__.py`, `pyproject.toml`, and `CHANGELOG.md` match
- **CHANGELOG format** — Keep a Changelog compliance
- **README content** — Features, install, configuration sections and badges
- **GitHub Workflows** — CI lint (black/isort/flake8) and release (PyPI publish)
- **Code linting** — Runs black, isort, flake8 against the plugin code
- **Package build** — Builds the package and validates with twine
- **Certification readiness** — Checks against the [NetBox Plugin Certification Program](https://github.com/netbox-community/netbox/wiki/Plugin-Certification-Program) requirements

## Requirements

- Python 3.10+
- Git (for cloning remote repos)
- Optional: black, isort, flake8 (for lint checks)
- Optional: build, twine (for packaging checks)

## Installation

### Docker (recommended)

```bash
docker run --rm ghcr.io/sieteunoseis/netbox-plugin-audit https://github.com/user/netbox-plugin
```

### pip

```bash
pip install netbox-plugin-audit[all]
```

### From source

```bash
git clone https://github.com/sieteunoseis/netbox-plugin-audit.git
cd netbox-plugin-audit
pip install -e ".[all]"
```

## Usage

Docker is the preferred way to run the tool — it includes all dependencies (git, black, isort, flake8, build, twine) out of the box.

```bash
# Audit a remote plugin (Docker)
docker run --rm ghcr.io/sieteunoseis/netbox-plugin-audit https://github.com/sieteunoseis/netbox-oxidized

# JSON output (for CI)
docker run --rm ghcr.io/sieteunoseis/netbox-plugin-audit --format json https://github.com/user/plugin

# Markdown output
docker run --rm ghcr.io/sieteunoseis/netbox-plugin-audit --format markdown https://github.com/user/plugin

# Strict mode (exit 1 on any warning)
docker run --rm ghcr.io/sieteunoseis/netbox-plugin-audit --strict https://github.com/user/plugin

# Skip slow checks
docker run --rm ghcr.io/sieteunoseis/netbox-plugin-audit --skip-lint --skip-build https://github.com/user/plugin

# Audit a local plugin (pip install)
netbox-plugin-audit /path/to/netbox-plugin
```

## Output

```
══════════════════════════════════════════════════════
  NetBox Plugin Audit Report
  Plugin: netbox_cisco_support (v1.0.9)
══════════════════════════════════════════════════════

  📁 Structure                                    9/9
    PASS  pyproject.toml exists
    PASS  README.md exists
    PASS  CHANGELOG.md exists
    ...

  ⚙️  PluginConfig                               17/17
    PASS  PluginConfig subclass: CiscoSupportConfig
    PASS  config = CiscoSupportConfig
    ...

  🏅 Certification                               11/14
    PASS  License file found: LICENSE
    PASS  License appears OSI-approved and Apache 2.0 compatible
    PASS  Version compatibility info found in README
    WARN  No test directory found (required for certification)
    ...

  ──────────────────────────────────────────────────
  Summary: 90/95 checks passed (95%)
    Errors: 0 | Warnings: 4 | Info: 1
```

## License

Apache License 2.0

# netbox-plugin-audit

Audit tool for validating NetBox plugin structure, metadata, and best practices.

Given a git URL (or local path), it clones the repo, runs ~80 checks across 10 categories, and outputs a color-coded report.

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

```bash
# Audit a remote plugin
netbox-plugin-audit https://github.com/sieteunoseis/netbox-oxidized

# Audit a local plugin
netbox-plugin-audit /path/to/netbox-plugin

# JSON output (for CI)
netbox-plugin-audit --format json https://github.com/user/plugin

# Markdown output
netbox-plugin-audit --format markdown https://github.com/user/plugin

# Strict mode (exit 1 on any warning)
netbox-plugin-audit --strict https://github.com/user/plugin

# Skip slow checks
netbox-plugin-audit --skip-lint --skip-build https://github.com/user/plugin
```

## Output

```
══════════════════════════════════════════════════════
  NetBox Plugin Audit Report
  Plugin: netbox_oxidized (v0.2.0)
══════════════════════════════════════════════════════

  📁 Structure                                    9/9
    PASS  pyproject.toml exists
    PASS  README.md exists
    PASS  CHANGELOG.md exists
    ...

  ⚙️  PluginConfig                                12/12
    PASS  PluginConfig subclass: OxidizedConfig
    PASS  config = OxidizedConfig
    ...

  ──────────────────────────────────────────────────
  Summary: 72/80 checks passed (90%)
    Errors: 0 | Warnings: 3 | Info: 5
```

## License

Apache License 2.0

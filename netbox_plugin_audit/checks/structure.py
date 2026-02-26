"""Check plugin file and directory structure."""

import os

from . import CategoryResult, CheckResult, Severity


def check_structure(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Check that required files and directories exist."""
    cat = CategoryResult(name="Structure", icon="F")
    results = cat.results

    # Required files (exact match)
    for fname, sev in [
        ("pyproject.toml", Severity.ERROR),
        ("README.md", Severity.ERROR),
        (".gitignore", Severity.WARNING),
    ]:
        if os.path.isfile(os.path.join(plugin_path, fname)):
            results.append(CheckResult(fname, Severity.PASS, f"{fname} exists"))
        else:
            results.append(CheckResult(fname, sev, f"{fname} not found"))

    # LICENSE - check common variants
    license_variants = ["LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE", "LICENCE.txt", "LICENCE.md"]
    found_license = None
    for variant in license_variants:
        if os.path.isfile(os.path.join(plugin_path, variant)):
            found_license = variant
            break
    if found_license:
        results.append(CheckResult("LICENSE", Severity.PASS, f"{found_license} exists"))
    else:
        results.append(CheckResult("LICENSE", Severity.WARNING, "No LICENSE file found"))

    # CHANGELOG - check common variants
    changelog_variants = [
        "CHANGELOG.md",
        "CHANGELOG.rst",
        "CHANGELOG.txt",
        "CHANGELOG",
        "CHANGES.md",
        "CHANGES.rst",
        "CHANGES.txt",
        "HISTORY.md",
        "HISTORY.rst",
    ]
    found_changelog = None
    for variant in changelog_variants:
        if os.path.isfile(os.path.join(plugin_path, variant)):
            found_changelog = variant
            break
    if found_changelog:
        results.append(CheckResult("CHANGELOG", Severity.PASS, f"{found_changelog} exists"))
    else:
        results.append(CheckResult("CHANGELOG", Severity.WARNING, "No CHANGELOG file found"))

    # Recommended files
    for fname, sev, msg in [
        ("CONTRIBUTING.md", Severity.INFO, "CONTRIBUTING.md not found (recommended)"),
        ("COMPATIBILITY.md", Severity.INFO, "COMPATIBILITY.md not found (recommended for version tracking)"),
        (".editorconfig", Severity.INFO, ".editorconfig not found (recommended for consistent formatting)"),
        (".pre-commit-config.yaml", Severity.INFO, ".pre-commit-config.yaml not found (recommended)"),
    ]:
        if os.path.isfile(os.path.join(plugin_path, fname)):
            results.append(CheckResult(fname, Severity.PASS, f"{fname} exists"))
        else:
            results.append(CheckResult(fname, sev, msg))

    # Docs directory
    docs_dir = os.path.join(plugin_path, "docs")
    if os.path.isdir(docs_dir):
        results.append(CheckResult("docs_dir", Severity.PASS, "docs/ directory exists"))
        mkdocs_path = os.path.join(plugin_path, "mkdocs.yml")
        if os.path.isfile(mkdocs_path):
            results.append(CheckResult("mkdocs", Severity.PASS, "mkdocs.yml exists"))
    else:
        results.append(
            CheckResult("docs_dir", Severity.INFO, "docs/ directory not found (recommended for extended docs)")
        )

    # Workflows directory
    wf_dir = os.path.join(plugin_path, ".github", "workflows")
    if os.path.isdir(wf_dir):
        results.append(CheckResult("workflows", Severity.PASS, ".github/workflows/ exists"))
    else:
        results.append(CheckResult("workflows", Severity.WARNING, ".github/workflows/ not found"))

    # Plugin package directory
    if pkg_dir:
        results.append(CheckResult("package_dir", Severity.PASS, f"Plugin package found: {pkg_dir}"))

        init_path = os.path.join(plugin_path, pkg_dir, "__init__.py")
        if os.path.isfile(init_path):
            results.append(CheckResult("init_py", Severity.PASS, "__init__.py exists"))
        else:
            results.append(CheckResult("init_py", Severity.ERROR, "__init__.py not found in package"))

        tmpl_dir = os.path.join(plugin_path, pkg_dir, "templates")
        if os.path.isdir(tmpl_dir):
            results.append(CheckResult("templates", Severity.PASS, "templates/ directory exists"))
        else:
            results.append(CheckResult("templates", Severity.INFO, "templates/ directory not found"))
    else:
        results.append(CheckResult("package_dir", Severity.ERROR, "No netbox_* package directory found"))

    return cat

"""Check version synchronization across files."""

import ast
import os
import re

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from . import CategoryResult, CheckResult, Severity


def _get_init_version(plugin_path: str, pkg_dir: str) -> str | None:
    """Extract __version__ from __init__.py."""
    init_path = os.path.join(plugin_path, pkg_dir, "__init__.py")
    if not os.path.isfile(init_path):
        return None
    try:
        with open(init_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__version__":
                        if isinstance(node.value, ast.Constant):
                            return str(node.value.value)
        return None
    except Exception:
        return None


def _get_pyproject_version(plugin_path: str) -> str | None:
    """Extract version from pyproject.toml."""
    toml_path = os.path.join(plugin_path, "pyproject.toml")
    if not os.path.isfile(toml_path):
        return None
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version")
    except Exception:
        return None


def _get_changelog_version(plugin_path: str) -> str | None:
    """Extract latest version from CHANGELOG.md."""
    cl_path = os.path.join(plugin_path, "CHANGELOG.md")
    if not os.path.isfile(cl_path):
        return None
    try:
        with open(cl_path) as f:
            content = f.read()
        match = re.search(r"##\s*\[(\d+\.\d+\.\d+)\]", content)
        return match.group(1) if match else None
    except Exception:
        return None


def check_versioning(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Check version synchronization across files."""
    cat = CategoryResult(name="Versioning", icon="V")
    results = cat.results

    if not pkg_dir:
        results.append(CheckResult("package", Severity.ERROR, "No package directory"))
        return cat

    init_ver = _get_init_version(plugin_path, pkg_dir)
    pyproj_ver = _get_pyproject_version(plugin_path)
    cl_ver = _get_changelog_version(plugin_path)

    # Check __version__ is valid semver
    if init_ver:
        if re.match(r"^\d+\.\d+\.\d+$", init_ver):
            results.append(CheckResult("semver", Severity.PASS, f"__version__ is valid semver: {init_ver}"))
        else:
            results.append(CheckResult("semver", Severity.WARNING, f"__version__ may not be semver: {init_ver}"))
    else:
        results.append(CheckResult("semver", Severity.ERROR, "__version__ not found in __init__.py"))

    # Check pyproject.toml matches __init__.py
    if init_ver and pyproj_ver:
        if init_ver == pyproj_ver:
            results.append(
                CheckResult("pyproject_match", Severity.PASS, f"pyproject.toml version matches ({pyproj_ver})")
            )
        else:
            results.append(
                CheckResult(
                    "pyproject_match",
                    Severity.ERROR,
                    f"Version mismatch: __init__.py={init_ver}, pyproject.toml={pyproj_ver}",
                )
            )
    elif not pyproj_ver:
        results.append(CheckResult("pyproject_match", Severity.ERROR, "No version in pyproject.toml"))

    # Check CHANGELOG matches (warning only)
    if init_ver and cl_ver:
        if init_ver == cl_ver:
            results.append(
                CheckResult("changelog_match", Severity.PASS, f"CHANGELOG latest version matches ({cl_ver})")
            )
        else:
            results.append(
                CheckResult(
                    "changelog_match",
                    Severity.WARNING,
                    f"CHANGELOG latest ({cl_ver}) != __version__ ({init_ver})",
                )
            )
    elif not cl_ver:
        results.append(CheckResult("changelog_match", Severity.INFO, "No version found in CHANGELOG.md"))

    return cat

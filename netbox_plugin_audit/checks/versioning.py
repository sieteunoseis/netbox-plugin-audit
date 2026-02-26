"""Check version synchronization across files."""

import ast
import os
import re

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from . import CategoryResult, CheckResult, Severity


def _get_init_version(plugin_path: str, pkg_dir: str) -> str | tuple[str, str] | None:
    """Extract __version__ from __init__.py or version.py.

    Returns:
        str: Static version string
        tuple: ("dynamic", pattern_name) for dynamic version (e.g. importlib.metadata)
        None: No version found
    """
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

        # Check for `from .version import __version__` pattern
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "version":
                for alias in node.names:
                    if alias.name == "__version__":
                        # Read from version.py
                        ver = _get_version_from_file(plugin_path, pkg_dir, "version.py")
                        if ver:
                            return ver

        # Check for importlib.metadata.version() usage (modern pattern)
        if "importlib.metadata" in source or "importlib import metadata" in source:
            if "metadata.version(" in source:
                return ("dynamic", "importlib.metadata")
        return None
    except Exception:
        return None


def _get_version_from_file(plugin_path: str, pkg_dir: str, filename: str) -> str | None:
    """Extract __version__ from a specific file (e.g. version.py)."""
    ver_path = os.path.join(plugin_path, pkg_dir, filename)
    if not os.path.isfile(ver_path):
        return None
    try:
        with open(ver_path) as f:
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
    """Extract latest version from changelog file."""
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
    cl_path = None
    for variant in changelog_variants:
        p = os.path.join(plugin_path, variant)
        if os.path.isfile(p):
            cl_path = p
            break
    if not cl_path:
        return None
    try:
        with open(cl_path) as f:
            content = f.read()
        match = re.search(r"##?\s*\[?(\d+\.\d+\.\d+)\]?", content)
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

    init_ver_raw = _get_init_version(plugin_path, pkg_dir)
    pyproj_ver = _get_pyproject_version(plugin_path)
    cl_ver = _get_changelog_version(plugin_path)

    # Handle dynamic version (importlib.metadata)
    is_dynamic = isinstance(init_ver_raw, tuple) and init_ver_raw[0] == "dynamic"
    init_ver = None if is_dynamic else init_ver_raw

    if is_dynamic:
        results.append(
            CheckResult(
                "semver",
                Severity.PASS,
                f"Version via {init_ver_raw[1]} (reads from pyproject.toml at runtime)",
            )
        )
        # For dynamic version, pyproject.toml is the source of truth
        if pyproj_ver:
            if re.match(r"^\d+\.\d+\.\d+$", pyproj_ver):
                results.append(CheckResult("pyproject_match", Severity.PASS, f"pyproject.toml version: {pyproj_ver}"))
            else:
                results.append(
                    CheckResult(
                        "pyproject_match", Severity.WARNING, f"pyproject.toml version may not be semver: {pyproj_ver}"
                    )
                )
        else:
            results.append(CheckResult("pyproject_match", Severity.ERROR, "No version in pyproject.toml"))
        # Use pyproject version for changelog comparison
        init_ver = pyproj_ver
    elif init_ver:
        # Check __version__ is valid semver
        if re.match(r"^\d+\.\d+\.\d+$", init_ver):
            results.append(CheckResult("semver", Severity.PASS, f"__version__ is valid semver: {init_ver}"))
        else:
            results.append(CheckResult("semver", Severity.WARNING, f"__version__ may not be semver: {init_ver}"))

        # Check pyproject.toml matches __init__.py
        if pyproj_ver:
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
        else:
            has_setup = os.path.isfile(os.path.join(plugin_path, "setup.py"))
            if has_setup:
                results.append(
                    CheckResult("pyproject_match", Severity.INFO, "Version in setup.py (consider pyproject.toml)")
                )
            else:
                results.append(CheckResult("pyproject_match", Severity.ERROR, "No version in pyproject.toml"))
    else:
        results.append(CheckResult("semver", Severity.ERROR, "__version__ not found in __init__.py"))
        if not pyproj_ver:
            has_setup = os.path.isfile(os.path.join(plugin_path, "setup.py"))
            if has_setup:
                results.append(
                    CheckResult("pyproject_match", Severity.INFO, "Version in setup.py (consider pyproject.toml)")
                )
            else:
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
                    f"CHANGELOG latest ({cl_ver}) != version ({init_ver})",
                )
            )
    elif not cl_ver:
        results.append(CheckResult("changelog_match", Severity.INFO, "No version found in changelog"))

    return cat

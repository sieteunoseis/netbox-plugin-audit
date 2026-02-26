"""Main auditor - clones repo, discovers plugin, runs all checks."""

import os
import shutil
import subprocess
import tempfile

from .checks import CategoryResult
from .checks.certification import check_certification
from .checks.changelog import check_changelog
from .checks.django_app import check_django_app
from .checks.linting import check_linting
from .checks.packaging import check_packaging
from .checks.pluginconfig import check_pluginconfig
from .checks.pyproject import check_pyproject
from .checks.readme import check_readme
from .checks.security import check_security
from .checks.structure import check_structure
from .checks.versioning import check_versioning
from .checks.workflows import check_workflows


def _detect_plugin_package(plugin_path: str) -> str | None:
    """Auto-detect the netbox_* package directory."""
    for entry in sorted(os.listdir(plugin_path)):
        full = os.path.join(plugin_path, entry)
        if os.path.isdir(full) and entry.startswith("netbox_") and os.path.isfile(os.path.join(full, "__init__.py")):
            return entry
    return None


def _get_plugin_version(plugin_path: str, pkg_dir: str) -> str | None:
    """Extract version from __init__.py."""
    import ast

    init_path = os.path.join(plugin_path, pkg_dir, "__init__.py")
    if not os.path.isfile(init_path):
        return None
    try:
        with open(init_path) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__version__":
                        if isinstance(node.value, ast.Constant):
                            return str(node.value.value)
    except Exception:
        pass
    return None


def _clone_repo(url: str, dest: str) -> bool:
    """Clone a git repository."""
    result = subprocess.run(
        ["git", "clone", "--depth", "1", url, dest],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode == 0


def audit_plugin(source: str, skip_lint: bool = False, skip_build: bool = False) -> dict:
    """
    Audit a NetBox plugin.

    Args:
        source: Git URL or local path to plugin
        skip_lint: Skip black/isort/flake8 checks
        skip_build: Skip package build test

    Returns:
        dict with keys: plugin_name, version, categories, summary
    """
    cleanup = False
    plugin_path = source

    # Clone if URL
    if source.startswith("http://") or source.startswith("https://") or source.startswith("git@"):
        tmpdir = tempfile.mkdtemp(prefix="nbaudit_")
        cleanup = True
        if not _clone_repo(source, tmpdir):
            return {
                "plugin_name": source,
                "version": None,
                "categories": [],
                "summary": {"total": 0, "passed": 0, "errors": 1, "warnings": 0, "infos": 0},
                "error": f"Failed to clone {source}",
            }
        plugin_path = tmpdir

    try:
        # Detect plugin package
        pkg_dir = _detect_plugin_package(plugin_path)

        # Get plugin info
        plugin_name = pkg_dir or os.path.basename(plugin_path.rstrip("/"))
        version = _get_plugin_version(plugin_path, pkg_dir) if pkg_dir else None

        # Run all checks
        categories: list[CategoryResult] = []

        categories.append(check_structure(plugin_path, pkg_dir))
        categories.append(check_pluginconfig(plugin_path, pkg_dir))
        categories.append(check_pyproject(plugin_path, pkg_dir))
        categories.append(check_versioning(plugin_path, pkg_dir))
        categories.append(check_changelog(plugin_path))
        categories.append(check_readme(plugin_path))
        categories.append(check_django_app(plugin_path, pkg_dir))
        categories.append(check_workflows(plugin_path, pkg_dir))
        categories.append(check_security(plugin_path, pkg_dir))
        categories.append(check_certification(plugin_path, pkg_dir))

        if not skip_lint:
            categories.append(check_linting(plugin_path, pkg_dir))

        if not skip_build:
            categories.append(check_packaging(plugin_path))

        # Build summary
        total = sum(c.total for c in categories)
        passed = sum(c.passed for c in categories)
        errors = sum(c.errors for c in categories)
        warnings = sum(c.warnings for c in categories)
        infos = sum(c.infos for c in categories)

        return {
            "plugin_name": plugin_name,
            "version": version,
            "categories": categories,
            "summary": {
                "total": total,
                "passed": passed,
                "errors": errors,
                "warnings": warnings,
                "infos": infos,
            },
        }
    finally:
        if cleanup and os.path.isdir(plugin_path):
            shutil.rmtree(plugin_path, ignore_errors=True)

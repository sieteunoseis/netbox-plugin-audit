"""Check GitHub Actions workflow configuration."""

import os
import re

from . import CategoryResult, CheckResult, Severity


def _read_yaml_simple(path: str) -> str:
    """Read YAML file as text (no yaml parser needed for simple checks)."""
    with open(path) as f:
        return f.read()


def check_workflows(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Validate GitHub Actions CI and release workflows."""
    cat = CategoryResult(name="Workflows", icon="W")
    results = cat.results

    wf_dir = os.path.join(plugin_path, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        results.append(CheckResult("workflows_dir", Severity.WARNING, ".github/workflows/ not found"))
        return cat

    # CI workflow
    ci_path = None
    for name in ["ci.yml", "ci.yaml", "lint.yml", "lint.yaml", "test.yml", "test.yaml"]:
        candidate = os.path.join(wf_dir, name)
        if os.path.isfile(candidate):
            ci_path = candidate
            break

    if ci_path:
        ci_content = _read_yaml_simple(ci_path)
        results.append(CheckResult("ci_exists", Severity.PASS, f"CI workflow found: {os.path.basename(ci_path)}"))

        # Check for lint tools (ruff or black+isort+flake8)
        if "ruff" in ci_content:
            results.append(CheckResult("ci_ruff", Severity.PASS, "ruff in CI workflow (modern linter)"))
        else:
            for tool_name in ["black", "isort", "flake8"]:
                if tool_name in ci_content:
                    results.append(CheckResult(f"ci_{tool_name}", Severity.PASS, f"{tool_name} in CI workflow"))
                else:
                    results.append(
                        CheckResult(f"ci_{tool_name}", Severity.WARNING, f"{tool_name} not found in CI workflow")
                    )

        # Check Python version matrix
        py_versions = re.findall(r"['\"]?(3\.1[0-9])['\"]?", ci_content)
        unique_versions = sorted(set(py_versions))
        if len(unique_versions) >= 2:
            results.append(CheckResult("ci_python_matrix", Severity.PASS, f"Tests Python {', '.join(unique_versions)}"))
        elif len(unique_versions) == 1:
            results.append(
                CheckResult(
                    "ci_python_matrix",
                    Severity.WARNING,
                    f"Only tests Python {unique_versions[0]} (recommend 3.10, 3.11, 3.12)",
                )
            )
        else:
            results.append(CheckResult("ci_python_matrix", Severity.INFO, "No Python version matrix detected"))

        # Check for package build
        if "build" in ci_content and "twine" in ci_content:
            results.append(CheckResult("ci_package", Severity.PASS, "Package build check in CI"))
        else:
            results.append(CheckResult("ci_package", Severity.INFO, "No package build check in CI"))
    else:
        results.append(CheckResult("ci_exists", Severity.WARNING, "No CI workflow found (ci.yml, lint.yml, test.yml)"))

    # Release workflow
    rel_path = None
    for name in ["release.yml", "release.yaml", "publish.yml", "publish.yaml"]:
        candidate = os.path.join(wf_dir, name)
        if os.path.isfile(candidate):
            rel_path = candidate
            break

    if rel_path:
        rel_content = _read_yaml_simple(rel_path)
        results.append(
            CheckResult("release_exists", Severity.PASS, f"Release workflow found: {os.path.basename(rel_path)}")
        )

        # Check tag trigger
        if re.search(r"tags.*v\*|tags.*\[.*v", rel_content):
            results.append(CheckResult("release_trigger", Severity.PASS, "Release triggers on tag push"))
        else:
            results.append(CheckResult("release_trigger", Severity.WARNING, "Release may not trigger on tag push"))

        # Check PyPI publish
        if "pypi" in rel_content.lower() or "gh-action-pypi-publish" in rel_content:
            results.append(CheckResult("release_pypi", Severity.PASS, "PyPI publish configured"))
        else:
            results.append(CheckResult("release_pypi", Severity.INFO, "No PyPI publish step detected"))

        # Check GitHub Release
        if (
            "gh-release" in rel_content
            or "action-gh-release" in rel_content
            or "create.*release" in rel_content.lower()
        ):
            results.append(CheckResult("release_github", Severity.PASS, "GitHub Release creation configured"))
        else:
            results.append(CheckResult("release_github", Severity.INFO, "No GitHub Release creation detected"))
    else:
        results.append(CheckResult("release_exists", Severity.WARNING, "No release workflow found"))

    return cat

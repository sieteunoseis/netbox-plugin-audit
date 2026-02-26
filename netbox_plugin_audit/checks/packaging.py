"""Check package build and validation."""

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request

from . import CategoryResult, CheckResult, Severity


def check_packaging(plugin_path: str) -> CategoryResult:
    """Build package and validate with twine."""
    cat = CategoryResult(name="Packaging", icon="B")
    results = cat.results

    if not os.path.isfile(os.path.join(plugin_path, "pyproject.toml")):
        results.append(CheckResult("pyproject", Severity.ERROR, "pyproject.toml not found, cannot build"))
        return cat

    # Build in a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            result = subprocess.run(
                ["python", "-m", "build", "--outdir", tmpdir],
                cwd=plugin_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                # Check what was built
                built_files = os.listdir(tmpdir)
                has_whl = any(f.endswith(".whl") for f in built_files)
                has_tar = any(f.endswith(".tar.gz") for f in built_files)
                results.append(CheckResult("build", Severity.PASS, f"Build succeeded: {', '.join(built_files)}"))

                if has_whl:
                    results.append(CheckResult("wheel", Severity.PASS, "Wheel (.whl) built"))
                else:
                    results.append(CheckResult("wheel", Severity.WARNING, "No wheel (.whl) built"))

                if has_tar:
                    results.append(CheckResult("sdist", Severity.PASS, "Source dist (.tar.gz) built"))
                else:
                    results.append(CheckResult("sdist", Severity.INFO, "No source dist (.tar.gz) built"))

                # Twine check
                try:
                    twine_result = subprocess.run(
                        ["python", "-m", "twine", "check"] + [os.path.join(tmpdir, f) for f in built_files],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if twine_result.returncode == 0:
                        results.append(CheckResult("twine", Severity.PASS, "twine check passed"))
                    else:
                        output = (twine_result.stdout + twine_result.stderr).strip()
                        results.append(CheckResult("twine", Severity.WARNING, f"twine check failed: {output[:200]}"))
                except FileNotFoundError:
                    results.append(CheckResult("twine", Severity.INFO, "twine not installed (skipped)"))
            else:
                error = (result.stdout + result.stderr).strip()
                # Truncate long error messages
                if len(error) > 300:
                    error = error[:300] + "..."
                results.append(CheckResult("build", Severity.ERROR, f"Build failed: {error}"))
        except FileNotFoundError:
            results.append(CheckResult("build", Severity.INFO, "python -m build not available (skipped)"))
        except subprocess.TimeoutExpired:
            results.append(CheckResult("build", Severity.WARNING, "Build timed out (120s)"))

    # --- PyPI presence check ---
    _check_pypi(plugin_path, results)

    return cat


def _check_pypi(plugin_path: str, results: list) -> None:
    """Check if the package exists on PyPI and compare versions."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return

    pyproject_path = os.path.join(plugin_path, "pyproject.toml")
    if not os.path.isfile(pyproject_path):
        return

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return

    pkg_name = data.get("project", {}).get("name", "")
    if not pkg_name:
        return

    local_version = data.get("project", {}).get("version", "")

    try:
        url = f"https://pypi.org/pypi/{pkg_name}/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            pypi_data = json.loads(resp.read().decode())

        pypi_version = pypi_data.get("info", {}).get("version", "")
        results.append(CheckResult("pypi_exists", Severity.PASS, f"{pkg_name} found on PyPI (latest: {pypi_version})"))

        # Compare versions
        if local_version and pypi_version:
            if local_version == pypi_version:
                results.append(
                    CheckResult("pypi_version", Severity.PASS, f"Local version matches PyPI ({local_version})")
                )
            else:
                results.append(
                    CheckResult(
                        "pypi_version",
                        Severity.INFO,
                        f"Local version ({local_version}) differs from PyPI ({pypi_version})",
                    )
                )

        # Check for project URLs on PyPI
        project_urls = pypi_data.get("info", {}).get("project_urls") or {}
        if project_urls:
            results.append(
                CheckResult("pypi_project_urls", Severity.PASS, f"PyPI project URLs: {', '.join(project_urls.keys())}")
            )
        else:
            results.append(CheckResult("pypi_project_urls", Severity.WARNING, "No project URLs on PyPI listing"))

    except urllib.error.HTTPError as e:
        if e.code == 404:
            results.append(
                CheckResult("pypi_exists", Severity.INFO, f"{pkg_name} not found on PyPI (not yet published?)")
            )
        else:
            results.append(CheckResult("pypi_exists", Severity.INFO, f"Could not check PyPI: HTTP {e.code}"))
    except Exception as e:
        results.append(CheckResult("pypi_exists", Severity.INFO, f"Could not check PyPI: {e}"))

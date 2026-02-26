"""Check package build and validation."""

import os
import subprocess
import tempfile

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

    return cat

"""Run code linting tools (black, isort, flake8)."""

import os
import subprocess

from . import CategoryResult, CheckResult, Severity


def _run_tool(cmd: list[str], cwd: str) -> tuple[int, str]:
    """Run a tool and return (returncode, output)."""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output
    except FileNotFoundError:
        return -1, f"{cmd[0]} not installed"
    except subprocess.TimeoutExpired:
        return -2, f"{cmd[0]} timed out"


def _check_ruff_available() -> bool:
    """Check if ruff is available."""
    try:
        result = subprocess.run(["ruff", "--version"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_linting(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Run linting checks (ruff or black+isort+flake8)."""
    cat = CategoryResult(name="Linting", icon="Q")
    results = cat.results

    if not pkg_dir:
        results.append(CheckResult("package", Severity.ERROR, "No package directory to lint"))
        return cat

    pkg_path = os.path.join(plugin_path, pkg_dir)
    if not os.path.isdir(pkg_path):
        results.append(CheckResult("package", Severity.ERROR, f"Package directory not found: {pkg_dir}"))
        return cat

    # Try ruff first (modern alternative)
    if _check_ruff_available():
        # Ruff check (linting)
        rc, output = _run_tool(["ruff", "check", pkg_dir + "/"], plugin_path)
        if rc == 0:
            results.append(CheckResult("ruff_check", Severity.PASS, "ruff check passed"))
        else:
            error_lines = [line for line in output.split("\n") if line.strip()]
            count = len(error_lines)
            results.append(CheckResult("ruff_check", Severity.WARNING, f"ruff found {count} issue(s)"))

        # Ruff format check
        rc, output = _run_tool(["ruff", "format", "--check", pkg_dir + "/"], plugin_path)
        if rc == 0:
            results.append(CheckResult("ruff_format", Severity.PASS, "ruff format check passed"))
        else:
            reformat_count = output.count("would reformat")
            results.append(
                CheckResult("ruff_format", Severity.WARNING, f"ruff would reformat {reformat_count} file(s)")
            )

    # Always run black+isort+flake8 (they are the standard for our plugins)
    # Black
    rc, output = _run_tool(["python", "-m", "black", "--check", pkg_dir + "/"], plugin_path)
    if rc == 0:
        results.append(CheckResult("black", Severity.PASS, "black formatting check passed"))
    elif rc == -1:
        results.append(CheckResult("black", Severity.INFO, "black not installed (skipped)"))
    else:
        reformat_count = output.count("would reformat")
        results.append(CheckResult("black", Severity.WARNING, f"black would reformat {reformat_count} file(s)"))

    # isort
    rc, output = _run_tool(["python", "-m", "isort", "--check-only", pkg_dir + "/"], plugin_path)
    if rc == 0:
        results.append(CheckResult("isort", Severity.PASS, "isort import check passed"))
    elif rc == -1:
        results.append(CheckResult("isort", Severity.INFO, "isort not installed (skipped)"))
    else:
        error_count = output.count("ERROR")
        results.append(CheckResult("isort", Severity.WARNING, f"isort found {error_count} import ordering issue(s)"))

    # flake8
    rc, output = _run_tool(
        ["python", "-m", "flake8", pkg_dir + "/", "--max-line-length=120", "--ignore=E501,W503,E203"],
        plugin_path,
    )
    if rc == 0:
        results.append(CheckResult("flake8", Severity.PASS, "flake8 lint check passed"))
    elif rc == -1:
        results.append(CheckResult("flake8", Severity.INFO, "flake8 not installed (skipped)"))
    else:
        error_lines = [line for line in output.split("\n") if line.strip()]
        count = len(error_lines)
        first_errors = error_lines[:3]
        msg = f"flake8 found {count} issue(s)"
        if first_errors:
            msg += ": " + "; ".join(first_errors)
        results.append(CheckResult("flake8", Severity.WARNING, msg))

    return cat

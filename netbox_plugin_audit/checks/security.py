"""Check for security patterns and potential issues."""

import os
import re

from . import CategoryResult, CheckResult, Severity

# Patterns that suggest hardcoded secrets
SECRET_PATTERNS = [
    (r"""(?:password|passwd|pwd)\s*=\s*['"][^'"]{3,}['"]""", "Hardcoded password"),
    (r"""(?:secret_key|api_key|apikey|token)\s*=\s*['"][^'"]{8,}['"]""", "Hardcoded secret/API key"),
    (r"""(?:SECRET_KEY)\s*=\s*['"][^'"]+['"]""", "Django SECRET_KEY in code"),
    (r"""(?:aws_access_key|aws_secret)\s*=\s*['"][^'"]+['"]""", "Hardcoded AWS credentials"),
]

# Files/dirs to skip during security scanning
SKIP_DIRS = {"migrations", "__pycache__", ".git", "node_modules", ".tox", ".eggs"}
SKIP_FILES = {"__pycache__", ".pyc"}


def _scan_python_files(pkg_path: str):
    """Yield (filepath, content) for all .py files in package."""
    for root, dirs, files in os.walk(pkg_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".py"):
                fpath = os.path.join(root, f)
                try:
                    with open(fpath) as fp:
                        yield fpath, fp.read()
                except Exception:
                    continue


def check_security(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Check for security issues and best practices."""
    cat = CategoryResult(name="Security", icon="S")
    results = cat.results

    if not pkg_dir:
        results.append(CheckResult("package", Severity.ERROR, "No package directory to check"))
        return cat

    pkg_path = os.path.join(plugin_path, pkg_dir)

    # --- Scan for hardcoded secrets ---
    secret_findings = []
    for fpath, content in _scan_python_files(pkg_path):
        rel_path = os.path.relpath(fpath, plugin_path)
        for pattern, desc in SECRET_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Filter out common false positives (empty strings, placeholders)
                real_matches = [
                    m
                    for m in matches
                    if not re.search(
                        r"""['"](?:changeme|replace|your_|example|xxx|placeholder|TODO|FIXME|default|test)""",
                        m,
                        re.IGNORECASE,
                    )
                ]
                if real_matches:
                    secret_findings.append(f"{rel_path}: {desc}")

    if not secret_findings:
        results.append(CheckResult("no_secrets", Severity.PASS, "No hardcoded secrets detected"))
    else:
        for finding in secret_findings[:5]:
            results.append(CheckResult("hardcoded_secret", Severity.WARNING, finding))

    # --- Check for verify=False in requests ---
    verify_false_files = []
    for fpath, content in _scan_python_files(pkg_path):
        rel_path = os.path.relpath(fpath, plugin_path)
        if re.search(r"verify\s*=\s*False", content):
            # Check if it's configurable (uses a settings variable)
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if re.search(r"verify\s*=\s*False", line):
                    # Check if nearby lines have settings/config reference
                    context = "\n".join(lines[max(0, i - 5) : i + 5])
                    if not re.search(r"settings|config|PLUGIN|get_plugin_config", context, re.IGNORECASE):
                        verify_false_files.append(f"{rel_path}:{i}")

    if not verify_false_files:
        results.append(CheckResult("ssl_verify", Severity.PASS, "No non-configurable verify=False found"))
    else:
        for loc in verify_false_files[:3]:
            results.append(CheckResult("ssl_verify", Severity.WARNING, f"verify=False not configurable: {loc}"))

    # --- Check requests usage has timeout ---
    missing_timeout = []
    for fpath, content in _scan_python_files(pkg_path):
        rel_path = os.path.relpath(fpath, plugin_path)
        # Find requests.get/post/put/delete/patch calls
        for match in re.finditer(r"requests\.(get|post|put|delete|patch)\(", content):
            # Get the full call (rough heuristic - find matching paren)
            start = match.start()
            # Look at a window of ~500 chars for the timeout parameter
            window = content[start : start + 500]
            if "timeout" not in window.split(")")[0]:
                line_num = content[:start].count("\n") + 1
                missing_timeout.append(f"{rel_path}:{line_num}")

    if not missing_timeout:
        results.append(CheckResult("request_timeout", Severity.PASS, "All requests calls include timeout"))
    else:
        for loc in missing_timeout[:3]:
            results.append(CheckResult("request_timeout", Severity.WARNING, f"requests call missing timeout: {loc}"))
        if len(missing_timeout) > 3:
            results.append(
                CheckResult(
                    "request_timeout",
                    Severity.WARNING,
                    f"... and {len(missing_timeout) - 3} more missing timeout(s)",
                )
            )

    # --- Check for permission mixins in views ---
    views_path = os.path.join(pkg_path, "views.py")
    views_dir = os.path.join(pkg_path, "views")
    view_files = []
    if os.path.isfile(views_path):
        view_files.append(views_path)
    if os.path.isdir(views_dir):
        for f in os.listdir(views_dir):
            if f.endswith(".py") and f != "__init__.py":
                view_files.append(os.path.join(views_dir, f))

    if view_files:
        has_permission_check = False
        for vf in view_files:
            try:
                with open(vf) as f:
                    view_content = f.read()
                if re.search(
                    r"PermissionRequiredMixin|LoginRequiredMixin|ObjectPermissionRequiredMixin|permission_required",
                    view_content,
                ):
                    has_permission_check = True
                    break
                # NetBox generic views include permissions by default
                if re.search(
                    r"ObjectView|ObjectListView|ObjectEditView|ObjectDeleteView|ObjectChildrenView|BulkEditView",
                    view_content,
                ):
                    has_permission_check = True
                    break
            except Exception:
                continue

        if has_permission_check:
            results.append(CheckResult("view_permissions", Severity.PASS, "Views use permission checks"))
        else:
            results.append(CheckResult("view_permissions", Severity.WARNING, "Views may lack permission checks"))

    # --- Check for .env or secrets files committed ---
    dangerous_files = [".env", ".env.local", "credentials.json", "secrets.yml", "secrets.yaml"]
    found_dangerous = []
    for df in dangerous_files:
        if os.path.isfile(os.path.join(plugin_path, df)):
            found_dangerous.append(df)

    if not found_dangerous:
        results.append(CheckResult("no_env_files", Severity.PASS, "No .env or credential files in repo"))
    else:
        for df in found_dangerous:
            results.append(CheckResult("env_file", Severity.WARNING, f"Sensitive file in repo: {df}"))

    # --- Check .gitignore covers common sensitive files ---
    gitignore_path = os.path.join(plugin_path, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path) as f:
            gitignore = f.read()
        if ".env" in gitignore:
            results.append(CheckResult("gitignore_env", Severity.PASS, ".env in .gitignore"))
        else:
            results.append(CheckResult("gitignore_env", Severity.INFO, ".env not in .gitignore"))
    return cat

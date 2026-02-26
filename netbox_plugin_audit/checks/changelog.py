"""Check changelog format and content."""

import json
import os
import re
import subprocess
import urllib.error
import urllib.request

from . import CategoryResult, CheckResult, Severity

# Common changelog file variants
CHANGELOG_VARIANTS = [
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


def _find_changelog(plugin_path: str) -> str | None:
    """Find changelog file, trying common variants."""
    for variant in CHANGELOG_VARIANTS:
        path = os.path.join(plugin_path, variant)
        if os.path.isfile(path):
            return path
    return None


def _get_github_repo(plugin_path: str) -> str | None:
    """Extract GitHub owner/repo from git remote URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=plugin_path,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        m = re.search(r"github\.com[/:]([^/]+/[^/.]+?)(?:\.git)?$", url)
        return m.group(1) if m else None
    except Exception:
        return None


def _check_github_releases(plugin_path: str, results: list) -> bool:
    """Check if the repo has GitHub releases. Returns True if releases found."""
    repo = _get_github_repo(plugin_path)
    if not repo:
        return False

    try:
        url = f"https://api.github.com/repos/{repo}/releases?per_page=5"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            releases = json.loads(resp.read().decode())

        if not releases:
            return False

        count = len(releases)
        latest = releases[0].get("tag_name", "unknown")
        has_body = any(r.get("body", "").strip() for r in releases)

        results.append(
            CheckResult(
                "github_releases",
                Severity.PASS,
                f"GitHub Releases found ({count}+ releases, latest: {latest})",
            )
        )

        if has_body:
            results.append(CheckResult("release_notes", Severity.PASS, "GitHub Releases include release notes"))
        else:
            results.append(CheckResult("release_notes", Severity.INFO, "GitHub Releases have no release notes body"))

        results.append(
            CheckResult(
                "changelog_suggestion",
                Severity.INFO,
                "Consider adding a CHANGELOG.md for offline/PyPI visibility",
            )
        )
        return True

    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def check_changelog(plugin_path: str) -> CategoryResult:
    """Validate changelog format and content."""
    cat = CategoryResult(name="CHANGELOG", icon="L")
    results = cat.results

    cl_path = _find_changelog(plugin_path)
    if not cl_path:
        # No changelog file — check GitHub Releases as alternative
        if _check_github_releases(plugin_path, results):
            return cat
        results.append(CheckResult("exists", Severity.WARNING, "No changelog file found"))
        return cat

    fname = os.path.basename(cl_path)
    results.append(CheckResult("exists", Severity.PASS, f"{fname} exists"))

    # Only do detailed format checks on markdown changelogs
    if not cl_path.endswith(".md"):
        results.append(CheckResult("format", Severity.INFO, f"{fname} found (detailed checks only for .md)"))
        return cat

    with open(cl_path) as f:
        content = f.read()
    lines = content.strip().split("\n")

    # Check header
    if lines and lines[0].strip().startswith("# Changelog"):
        results.append(CheckResult("header", Severity.PASS, "Starts with # Changelog"))
    elif lines and lines[0].strip().startswith("# "):
        results.append(CheckResult("header", Severity.INFO, f"Header: {lines[0].strip()} (expected # Changelog)"))
    else:
        results.append(CheckResult("header", Severity.WARNING, "Missing # Changelog header"))

    # Check for Unreleased section
    if re.search(r"##\s*\[?Unreleased\]?", content, re.IGNORECASE):
        results.append(CheckResult("unreleased", Severity.PASS, "[Unreleased] section found"))
    else:
        results.append(CheckResult("unreleased", Severity.INFO, "No [Unreleased] section"))

    # Check version sections
    version_matches = re.findall(r"##\s*\[(\d+\.\d+\.\d+)\]\s*-\s*(\d{4}-\d{2}-\d{2})", content)
    if version_matches:
        results.append(CheckResult("versions", Severity.PASS, f"{len(version_matches)} version entries found"))

        # Check date validity
        valid_dates = True
        for ver, date in version_matches:
            parts = date.split("-")
            try:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                if not (2020 <= y <= 2030 and 1 <= m <= 12 and 1 <= d <= 31):
                    valid_dates = False
            except (ValueError, IndexError):
                valid_dates = False

        if valid_dates:
            results.append(CheckResult("dates", Severity.PASS, "All dates are valid YYYY-MM-DD"))
        else:
            results.append(CheckResult("dates", Severity.WARNING, "Some dates may be invalid"))
    else:
        # Check for versions without dates
        ver_only = re.findall(r"##\s*\[(\d+\.\d+\.\d+)\]", content)
        if ver_only:
            results.append(
                CheckResult(
                    "versions",
                    Severity.WARNING,
                    f"{len(ver_only)} versions found but missing dates (expected ## [X.Y.Z] - YYYY-MM-DD)",
                )
            )
        else:
            results.append(CheckResult("versions", Severity.WARNING, "No version entries found"))

    # Check for subsections (Added, Fixed, Changed, etc.)
    subsections = re.findall(r"###\s*(Added|Fixed|Changed|Removed|Deprecated|Security)", content)
    if subsections:
        unique = set(subsections)
        results.append(CheckResult("subsections", Severity.PASS, f"Subsections used: {', '.join(sorted(unique))}"))
    else:
        results.append(
            CheckResult("subsections", Severity.INFO, "No standard subsections (Added, Fixed, Changed, etc.)")
        )

    # Check Keep a Changelog reference
    if "keepachangelog" in content.lower() or "keep a changelog" in content.lower():
        results.append(CheckResult("format_ref", Severity.PASS, "References Keep a Changelog format"))
    else:
        results.append(CheckResult("format_ref", Severity.INFO, "No reference to Keep a Changelog format"))

    return cat

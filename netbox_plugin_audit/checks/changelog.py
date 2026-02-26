"""Check CHANGELOG.md format and content."""

import os
import re

from . import CategoryResult, CheckResult, Severity


def check_changelog(plugin_path: str) -> CategoryResult:
    """Validate CHANGELOG.md follows Keep a Changelog format."""
    cat = CategoryResult(name="CHANGELOG", icon="L")
    results = cat.results

    cl_path = os.path.join(plugin_path, "CHANGELOG.md")
    if not os.path.isfile(cl_path):
        results.append(CheckResult("exists", Severity.WARNING, "CHANGELOG.md not found"))
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

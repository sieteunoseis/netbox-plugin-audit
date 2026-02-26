"""Check README.md content and sections."""

import os
import re

from . import CategoryResult, CheckResult, Severity


def check_readme(plugin_path: str) -> CategoryResult:
    """Validate README.md has required sections and content."""
    cat = CategoryResult(name="README", icon="R")
    results = cat.results

    readme_path = os.path.join(plugin_path, "README.md")
    if not os.path.isfile(readme_path):
        results.append(CheckResult("exists", Severity.ERROR, "README.md not found"))
        return cat

    with open(readme_path) as f:
        content = f.read()

    # Minimum length
    if len(content) >= 500:
        results.append(CheckResult("length", Severity.PASS, f"README length: {len(content)} chars"))
    else:
        results.append(
            CheckResult("length", Severity.WARNING, f"README is short ({len(content)} chars, recommend 500+)")
        )

    # Check for key sections
    sections = [
        ("features", r"(?:^|\n)#{1,3}\s*features", Severity.WARNING),
        ("install", r"(?:^|\n)#{1,3}\s*install", Severity.WARNING),
        ("configuration", r"PLUGINS_CONFIG|(?:^|\n)#{1,3}\s*config", Severity.WARNING),
        ("requirements", r"(?:^|\n)#{1,3}\s*requirements|netbox.*\d+\.\d+|python.*3\.\d+", Severity.INFO),
    ]

    for name, pattern, sev in sections:
        if re.search(pattern, content, re.IGNORECASE):
            results.append(CheckResult(name, Severity.PASS, f"{name.title()} section found"))
        else:
            results.append(CheckResult(name, sev, f"{name.title()} section not found"))

    # Check for badges
    badge_patterns = [
        r"\!\[.*\]\(.*shields\.io",
        r"\!\[.*\]\(.*badge",
        r"\!\[.*\]\(.*img\.shields",
        r"<img.*badge",
    ]
    has_badge = any(re.search(p, content) for p in badge_patterns)
    if has_badge:
        results.append(CheckResult("badges", Severity.PASS, "Badge(s) found"))
    else:
        results.append(CheckResult("badges", Severity.INFO, "No badges found (consider adding version/license badges)"))

    # Check for screenshots
    img_patterns = [r"\!\[.*\]\(.*\.(png|jpg|jpeg|gif)", r"<img.*src="]
    has_images = any(re.search(p, content, re.IGNORECASE) for p in img_patterns)
    if has_images:
        results.append(CheckResult("screenshots", Severity.PASS, "Screenshots/images found"))
    else:
        results.append(CheckResult("screenshots", Severity.INFO, "No screenshots found"))

    return cat

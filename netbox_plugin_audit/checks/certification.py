"""Check NetBox Plugin Certification Program requirements.

Based on: https://github.com/netbox-community/netbox/wiki/Plugin-Certification-Program
"""

import os
import re

from . import CategoryResult, CheckResult, Severity

# OSI-approved licenses compatible with Apache 2.0
COMPATIBLE_LICENSES = [
    "apache",
    "mit",
    "bsd",
    "cddl",
    "lgpl",
    "gpl",
    "mpl",
    "epl",
    "isc",
]


def check_certification(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Check requirements for the NetBox Plugin Certification Program."""
    cat = CategoryResult(name="Certification", icon="T")
    results = cat.results

    # --- License checks ---
    license_path = None
    for name in ["LICENSE", "LICENSE.md", "LICENSE.txt"]:
        p = os.path.join(plugin_path, name)
        if os.path.isfile(p):
            license_path = p
            break

    if license_path:
        results.append(
            CheckResult("license_file", Severity.PASS, f"License file found: {os.path.basename(license_path)}")
        )
        with open(license_path) as f:
            license_text = f.read().lower()
        is_compatible = any(lic in license_text for lic in COMPATIBLE_LICENSES)
        if is_compatible:
            results.append(
                CheckResult("license_osi", Severity.PASS, "License appears OSI-approved and Apache 2.0 compatible")
            )
        else:
            results.append(
                CheckResult("license_osi", Severity.WARNING, "License may not be OSI-approved or Apache 2.0 compatible")
            )
    else:
        results.append(
            CheckResult("license_file", Severity.ERROR, "No LICENSE file found (required for certification)")
        )

    # --- README checks specific to certification ---
    readme_path = os.path.join(plugin_path, "README.md")
    if os.path.isfile(readme_path):
        with open(readme_path) as f:
            readme = f.read()

        # Version compatibility matrix
        has_compat = bool(
            re.search(
                r"compat|version.*matrix|version.*range|netbox.*version|supported.*version", readme, re.IGNORECASE
            )
        )
        if has_compat:
            results.append(CheckResult("compat_matrix", Severity.PASS, "Version compatibility info found in README"))
        else:
            results.append(
                CheckResult(
                    "compat_matrix",
                    Severity.WARNING,
                    "No version compatibility matrix in README (required for certification)",
                )
            )

        # Dependencies section
        has_deps = bool(re.search(r"(?:^|\n)#{1,3}\s*depend|requirements|prerequisites", readme, re.IGNORECASE))
        if has_deps:
            results.append(CheckResult("deps_documented", Severity.PASS, "Dependencies documented in README"))
        else:
            results.append(CheckResult("deps_documented", Severity.INFO, "No dependencies section in README"))

        # Screenshots or screen recordings
        img_patterns = [
            r"!\[.*\]\(.*\.(png|jpg|jpeg|gif|svg|webp)",
            r"<img.*src=",
            r"!\[.*\]\(.*recording",
            r"!\[.*\]\(.*demo",
            r"!\[.*\]\(.*screenshot",
        ]
        has_screenshots = any(re.search(p, readme, re.IGNORECASE) for p in img_patterns)
        if has_screenshots:
            results.append(CheckResult("screenshots", Severity.PASS, "Screenshots/recordings found in README"))
        else:
            results.append(
                CheckResult(
                    "screenshots",
                    Severity.WARNING,
                    "No screenshots or recordings in README (required for certification)",
                )
            )

        # Installation instructions
        has_install = bool(re.search(r"(?:^|\n)#{1,3}\s*install|pip install", readme, re.IGNORECASE))
        if has_install:
            results.append(CheckResult("install_docs", Severity.PASS, "Installation instructions found"))
        else:
            results.append(CheckResult("install_docs", Severity.WARNING, "No installation instructions in README"))

        # Support / contact info
        has_support = bool(re.search(r"support|contact|issues|bug.*report|contribute|community", readme, re.IGNORECASE))
        if has_support:
            results.append(CheckResult("support_info", Severity.PASS, "Support/contact info found in README"))
        else:
            results.append(CheckResult("support_info", Severity.INFO, "No support/contact section in README"))
    else:
        results.append(CheckResult("readme_cert", Severity.ERROR, "README.md missing (required for certification)"))

    # --- Icon ---
    icon_patterns = ["icon.png", "icon.svg", "logo.png", "logo.svg"]
    has_icon = False
    for pattern in icon_patterns:
        # Check root and docs/ directories
        for search_dir in ["", "docs", "images", "assets", "static"]:
            check_path = (
                os.path.join(plugin_path, search_dir, pattern) if search_dir else os.path.join(plugin_path, pattern)
            )
            if os.path.isfile(check_path):
                has_icon = True
                break
        if has_icon:
            break

    if has_icon:
        results.append(CheckResult("icon", Severity.PASS, "Plugin icon found"))
    else:
        results.append(CheckResult("icon", Severity.INFO, "No plugin icon found (recommended for certification)"))

    # --- Test coverage ---
    test_dirs = ["tests", "test"]
    has_tests = False
    test_count = 0
    for td in test_dirs:
        test_path = os.path.join(plugin_path, td)
        if pkg_dir:
            pkg_test_path = os.path.join(plugin_path, pkg_dir, td)
            if os.path.isdir(pkg_test_path):
                has_tests = True
                test_count = _count_test_files(pkg_test_path)
                break
        if os.path.isdir(test_path):
            has_tests = True
            test_count = _count_test_files(test_path)
            break

    if has_tests and test_count > 0:
        results.append(CheckResult("tests_exist", Severity.PASS, f"Test directory found ({test_count} test files)"))
    elif has_tests:
        results.append(CheckResult("tests_exist", Severity.WARNING, "Test directory found but no test files"))
    else:
        results.append(
            CheckResult("tests_exist", Severity.WARNING, "No test directory found (required for certification)")
        )

    # --- CI/CD running tests ---
    wf_dir = os.path.join(plugin_path, ".github", "workflows")
    ci_runs_tests = False
    if os.path.isdir(wf_dir):
        for wf_file in os.listdir(wf_dir):
            wf_path = os.path.join(wf_dir, wf_file)
            if os.path.isfile(wf_path) and wf_file.endswith((".yml", ".yaml")):
                with open(wf_path) as f:
                    wf_content = f.read().lower()
                if "pytest" in wf_content or "python -m test" in wf_content or "manage.py test" in wf_content:
                    ci_runs_tests = True
                    break

    if ci_runs_tests:
        results.append(CheckResult("ci_tests", Severity.PASS, "CI workflow runs tests"))
    else:
        results.append(
            CheckResult("ci_tests", Severity.WARNING, "No CI workflow running tests (required for certification)")
        )

    # --- Release notes / CHANGELOG ---
    changelog_path = os.path.join(plugin_path, "CHANGELOG.md")
    if os.path.isfile(changelog_path):
        with open(changelog_path) as f:
            cl_content = f.read()

        # Check for breaking changes documentation pattern
        has_breaking = bool(re.search(r"breaking|backward|incompatible|migration", cl_content, re.IGNORECASE))
        if has_breaking:
            results.append(CheckResult("breaking_changes", Severity.PASS, "Breaking changes documented in CHANGELOG"))
        else:
            results.append(
                CheckResult("breaking_changes", Severity.INFO, "No breaking changes noted (OK if none exist)")
            )
    else:
        results.append(
            CheckResult("changelog_cert", Severity.WARNING, "CHANGELOG.md missing (required for certification)")
        )

    # --- Contributing guide ---
    contrib_files = ["CONTRIBUTING.md", "CONTRIBUTING.rst", ".github/CONTRIBUTING.md"]
    has_contrib = any(os.path.isfile(os.path.join(plugin_path, f)) for f in contrib_files)
    if has_contrib:
        results.append(CheckResult("contributing", Severity.PASS, "CONTRIBUTING guide found"))
    else:
        results.append(
            CheckResult("contributing", Severity.INFO, "No CONTRIBUTING guide (recommended for certification)")
        )

    # --- PyPI package metadata ---
    pyproject_path = os.path.join(plugin_path, "pyproject.toml")
    if os.path.isfile(pyproject_path):
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        project = data.get("project", {})

        # Check license in pyproject matches LICENSE file
        license_val = project.get("license", {})
        if license_val:
            results.append(CheckResult("pypi_license", Severity.PASS, "License declared in pyproject.toml"))
        else:
            results.append(
                CheckResult("pypi_license", Severity.WARNING, "No license in pyproject.toml (must match PyPI listing)")
            )

        # Check for project URLs (needed for PyPI listing)
        urls = project.get("urls", {})
        if urls:
            results.append(CheckResult("pypi_urls", Severity.PASS, f"Project URLs configured ({len(urls)} URLs)"))
        else:
            results.append(CheckResult("pypi_urls", Severity.WARNING, "No project URLs in pyproject.toml"))

    return cat


def _count_test_files(test_dir: str) -> int:
    """Count test_*.py and *_test.py files in a directory tree."""
    count = 0
    for root, _dirs, files in os.walk(test_dir):
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                count += 1
            elif f.endswith("_test.py"):
                count += 1
    return count

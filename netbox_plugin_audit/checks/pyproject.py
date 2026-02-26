"""Check pyproject.toml configuration."""

import os

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from . import CategoryResult, CheckResult, Severity


def check_pyproject(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Validate pyproject.toml structure and content."""
    cat = CategoryResult(name="pyproject.toml", icon="P")
    results = cat.results

    toml_path = os.path.join(plugin_path, "pyproject.toml")
    if not os.path.isfile(toml_path):
        results.append(CheckResult("exists", Severity.ERROR, "pyproject.toml not found"))
        return cat

    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        results.append(CheckResult("parse", Severity.ERROR, f"Failed to parse pyproject.toml: {e}"))
        return cat

    # Build system
    bs = data.get("build-system", {})
    if bs:
        requires = bs.get("requires", [])
        if any("setuptools" in r for r in requires):
            results.append(CheckResult("build_system", Severity.PASS, "setuptools build system configured"))
        else:
            results.append(CheckResult("build_system", Severity.WARNING, "Build system doesn't use setuptools"))
    else:
        results.append(CheckResult("build_system", Severity.ERROR, "[build-system] section missing"))

    # Project metadata
    project = data.get("project", {})
    if not project:
        results.append(CheckResult("project", Severity.ERROR, "[project] section missing"))
        return cat

    # Required fields
    required_fields = ["name", "version", "description", "readme", "requires-python", "authors"]
    for field_name in required_fields:
        if field_name in project:
            results.append(CheckResult(f"project_{field_name}", Severity.PASS, f"project.{field_name} set"))
        else:
            results.append(CheckResult(f"project_{field_name}", Severity.ERROR, f"project.{field_name} missing"))

    # Optional but recommended
    for field_name in ["license", "classifiers", "keywords", "dependencies"]:
        if field_name in project:
            results.append(CheckResult(f"project_{field_name}", Severity.PASS, f"project.{field_name} set"))
        else:
            results.append(CheckResult(f"project_{field_name}", Severity.WARNING, f"project.{field_name} missing"))

    # License check
    license_val = project.get("license", {})
    if isinstance(license_val, dict) and "Apache" in license_val.get("text", ""):
        results.append(CheckResult("license_type", Severity.PASS, "License is Apache-2.0"))
    elif isinstance(license_val, str) and "Apache" in license_val:
        results.append(CheckResult("license_type", Severity.PASS, "License is Apache-2.0"))
    elif license_val:
        results.append(CheckResult("license_type", Severity.INFO, f"License: {license_val}"))

    # requires-python check
    req_python = project.get("requires-python", "")
    if "3.10" in req_python or "3.11" in req_python or "3.12" in req_python:
        results.append(CheckResult("python_version", Severity.PASS, f"requires-python: {req_python}"))
    elif req_python:
        results.append(
            CheckResult("python_version", Severity.WARNING, f"requires-python: {req_python} (expected >=3.10)")
        )

    # Classifiers
    classifiers = project.get("classifiers", [])
    has_django = any("Django" in c for c in classifiers)
    has_py3 = any("Python :: 3" in c for c in classifiers)
    if has_django:
        results.append(CheckResult("classifier_django", Severity.PASS, "Framework :: Django classifier present"))
    else:
        results.append(CheckResult("classifier_django", Severity.WARNING, "Missing Framework :: Django classifier"))
    if has_py3:
        results.append(CheckResult("classifier_python", Severity.PASS, "Python 3 classifiers present"))
    else:
        results.append(CheckResult("classifier_python", Severity.WARNING, "Missing Python 3 classifiers"))

    # Project URLs
    urls = project.get("urls", data.get("project", {}).get("urls", {}))
    expected_urls = ["Homepage", "Repository", "Issues", "Documentation", "Changelog"]
    for url_name in expected_urls:
        if url_name in urls:
            results.append(CheckResult(f"url_{url_name.lower()}", Severity.PASS, f"{url_name} URL set"))
        else:
            results.append(CheckResult(f"url_{url_name.lower()}", Severity.WARNING, f"{url_name} URL missing"))

    # Dev dependencies
    opt_deps = project.get("optional-dependencies", data.get("project", {}).get("optional-dependencies", {}))
    dev_deps = opt_deps.get("dev", [])
    if dev_deps:
        dev_str = ", ".join(dev_deps)
        results.append(CheckResult("dev_deps", Severity.PASS, f"Dev dependencies: {dev_str}"))
        for tool in ["black", "flake8", "isort"]:
            if any(tool in d for d in dev_deps):
                results.append(CheckResult(f"dev_{tool}", Severity.PASS, f"{tool} in dev dependencies"))
            else:
                results.append(CheckResult(f"dev_{tool}", Severity.WARNING, f"{tool} missing from dev dependencies"))
    else:
        results.append(CheckResult("dev_deps", Severity.WARNING, "No [project.optional-dependencies] dev section"))

    # Tool configuration
    tool = data.get("tool", {})

    # Setuptools
    pkg_find = tool.get("setuptools", {}).get("packages", {}).get("find", {})
    if pkg_find:
        results.append(CheckResult("setuptools_find", Severity.PASS, "setuptools packages.find configured"))
    else:
        results.append(CheckResult("setuptools_find", Severity.WARNING, "setuptools packages.find not configured"))

    pkg_data = tool.get("setuptools", {}).get("package-data", {})
    if pkg_data:
        results.append(CheckResult("package_data", Severity.PASS, "package-data configured for templates"))
    else:
        results.append(CheckResult("package_data", Severity.WARNING, "package-data not configured"))

    # Black config
    black_cfg = tool.get("black", {})
    if black_cfg:
        line_len = black_cfg.get("line-length")
        results.append(CheckResult("black_config", Severity.PASS, f"[tool.black] configured (line-length={line_len})"))
    else:
        results.append(CheckResult("black_config", Severity.WARNING, "[tool.black] section missing"))

    # Isort config
    isort_cfg = tool.get("isort", {})
    if isort_cfg:
        profile = isort_cfg.get("profile", "")
        if profile == "black":
            results.append(CheckResult("isort_config", Severity.PASS, '[tool.isort] profile = "black"'))
        else:
            results.append(
                CheckResult("isort_config", Severity.WARNING, f'[tool.isort] profile = "{profile}" (expected "black")')
            )

        # Check line length consistency
        isort_len = isort_cfg.get("line_length")
        black_len = black_cfg.get("line-length")
        if isort_len and black_len and isort_len == black_len:
            results.append(
                CheckResult("line_length_match", Severity.PASS, f"isort/black line-length match ({black_len})")
            )
        elif isort_len and black_len:
            results.append(
                CheckResult(
                    "line_length_match",
                    Severity.WARNING,
                    f"isort ({isort_len}) != black ({black_len}) line-length",
                )
            )
    else:
        results.append(CheckResult("isort_config", Severity.WARNING, "[tool.isort] section missing"))

    return cat

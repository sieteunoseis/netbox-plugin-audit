"""Check PluginConfig class in __init__.py via AST parsing."""

import ast
import os
import re

from . import CategoryResult, CheckResult, Severity


def _extract_string_value(node):
    """Extract string value from AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_assignments(tree):
    """Extract top-level assignments from AST."""
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    val = _extract_string_value(node.value)
                    if val is not None:
                        assignments[target.id] = val
    return assignments


def _find_pluginconfig_class(tree):
    """Find class that inherits from PluginConfig."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = None
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if base_name == "PluginConfig":
                    return node
    return None


def _is_importlib_metadata_version(node):
    """Check if AST node is importlib.metadata.version(...) call."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    # importlib.metadata.version("pkg")
    if isinstance(func, ast.Attribute) and func.attr == "version":
        if isinstance(func.value, ast.Attribute) and func.value.attr == "metadata":
            return True
    # metadata.version("pkg") after `from importlib import metadata`
    if isinstance(func, ast.Attribute) and func.attr == "version":
        if isinstance(func.value, ast.Name) and func.value.id == "metadata":
            return True
    return False


def _get_class_attributes(class_node):
    """Extract class-level attribute assignments."""
    attrs = {}
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    val = _extract_string_value(node.value)
                    if val is not None:
                        attrs[target.id] = val
                    elif isinstance(node.value, ast.Name):
                        attrs[target.id] = f"__ref__{node.value.id}"
                    elif isinstance(node.value, (ast.Dict, ast.List)):
                        attrs[target.id] = "__present__"
                    elif _is_importlib_metadata_version(node.value):
                        attrs[target.id] = "__dynamic_version__"
    return attrs


def _find_config_assignment(tree):
    """Find `config = ClassName` assignment."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "config":
                    if isinstance(node.value, ast.Name):
                        return node.value.id
    return None


def check_pluginconfig(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Validate PluginConfig class attributes."""
    cat = CategoryResult(name="PluginConfig", icon="C")
    results = cat.results

    if not pkg_dir:
        results.append(CheckResult("package", Severity.ERROR, "No package directory to check"))
        return cat

    init_path = os.path.join(plugin_path, pkg_dir, "__init__.py")
    if not os.path.isfile(init_path):
        results.append(CheckResult("init_py", Severity.ERROR, "__init__.py not found"))
        return cat

    try:
        with open(init_path) as f:
            source = f.read()
        tree = ast.parse(source)
    except SyntaxError as e:
        results.append(CheckResult("parse", Severity.ERROR, f"Syntax error in __init__.py: {e}"))
        return cat

    # Find PluginConfig subclass
    config_class = _find_pluginconfig_class(tree)
    if not config_class:
        results.append(CheckResult("pluginconfig_class", Severity.ERROR, "No PluginConfig subclass found"))
        return cat
    results.append(CheckResult("pluginconfig_class", Severity.PASS, f"PluginConfig subclass: {config_class.name}"))

    # Check config assignment
    config_name = _find_config_assignment(tree)
    if config_name:
        if config_name == config_class.name:
            results.append(CheckResult("config_assignment", Severity.PASS, f"config = {config_name}"))
        else:
            results.append(
                CheckResult(
                    "config_assignment",
                    Severity.WARNING,
                    f"config = {config_name} (expected {config_class.name})",
                )
            )
    else:
        results.append(CheckResult("config_assignment", Severity.ERROR, "No `config = ClassName` assignment found"))

    # Get class attributes
    attrs = _get_class_attributes(config_class)
    top_assignments = _extract_assignments(tree)

    # Required attributes (ERROR if missing)
    required = ["name", "verbose_name", "description", "version", "base_url", "min_version"]
    for attr in required:
        if attr in attrs:
            val = attrs[attr]
            if val == "__dynamic_version__":
                results.append(CheckResult(attr, Severity.PASS, f"{attr} set (via importlib.metadata)"))
            elif val.startswith("__ref__"):
                results.append(CheckResult(attr, Severity.PASS, f"{attr} set (references {val[7:]})"))
            else:
                display = val[:60] + "..." if len(val) > 60 else val
                results.append(CheckResult(attr, Severity.PASS, f'{attr} = "{display}"'))
        else:
            results.append(CheckResult(attr, Severity.ERROR, f"{attr} not set"))

    # Recommended attributes (WARNING if missing — may be in pyproject.toml instead)
    for attr in ["author", "author_email"]:
        if attr in attrs:
            val = attrs[attr]
            if val.startswith("__ref__"):
                results.append(CheckResult(attr, Severity.PASS, f"{attr} set (references {val[7:]})"))
            else:
                display = val[:60] + "..." if len(val) > 60 else val
                results.append(CheckResult(attr, Severity.PASS, f'{attr} = "{display}"'))
        else:
            results.append(CheckResult(attr, Severity.WARNING, f"{attr} not set in PluginConfig"))

    # Recommended attributes
    if "max_version" in attrs:
        results.append(CheckResult("max_version", Severity.PASS, f'max_version = "{attrs["max_version"]}"'))
    else:
        results.append(CheckResult("max_version", Severity.WARNING, "max_version not set"))

    if "default_settings" in attrs:
        results.append(CheckResult("default_settings", Severity.PASS, "default_settings defined"))
    else:
        results.append(CheckResult("default_settings", Severity.INFO, "default_settings not defined"))

    # Validate name matches directory
    if "name" in attrs and not attrs["name"].startswith("__ref__"):
        if attrs["name"] == pkg_dir:
            results.append(CheckResult("name_match", Severity.PASS, "name matches package directory"))
        else:
            results.append(
                CheckResult("name_match", Severity.WARNING, f'name "{attrs["name"]}" != directory "{pkg_dir}"')
            )

    # Validate author_email format
    if "author_email" in attrs and not attrs["author_email"].startswith("__ref__"):
        email = attrs["author_email"]
        if re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            results.append(CheckResult("email_format", Severity.PASS, f"Valid email: {email}"))
        else:
            results.append(CheckResult("email_format", Severity.WARNING, f"Invalid email format: {email}"))

    # Validate base_url is URL-safe
    if "base_url" in attrs and not attrs["base_url"].startswith("__ref__"):
        base_url = attrs["base_url"]
        if re.match(r"^[a-z0-9-]+$", base_url):
            results.append(CheckResult("base_url_format", Severity.PASS, f"URL-safe base_url: {base_url}"))
        else:
            results.append(
                CheckResult("base_url_format", Severity.WARNING, f"base_url may not be URL-safe: {base_url}")
            )

    # Validate min_version
    if "min_version" in attrs and not attrs["min_version"].startswith("__ref__"):
        min_ver = attrs["min_version"]
        try:
            major = int(min_ver.split(".")[0])
            if major >= 4:
                results.append(CheckResult("min_version_value", Severity.PASS, f"min_version {min_ver} >= 4.0.0"))
            else:
                results.append(
                    CheckResult(
                        "min_version_value", Severity.WARNING, f"min_version {min_ver} < 4.0.0 (consider 4.0.0+)"
                    )
                )
        except (ValueError, IndexError):
            pass

    # Check ready() method for widget import (only if widgets.py exists with widget classes)
    widgets_path = os.path.join(plugin_path, pkg_dir, "widgets.py")
    if os.path.isfile(widgets_path):
        # Quick check: does widgets.py contain DashboardWidget subclasses?
        has_widget_classes = False
        try:
            with open(widgets_path) as f:
                widgets_tree = ast.parse(f.read())
            for wnode in ast.iter_child_nodes(widgets_tree):
                if isinstance(wnode, ast.ClassDef):
                    for base in wnode.bases:
                        bname = None
                        if isinstance(base, ast.Name):
                            bname = base.id
                        elif isinstance(base, ast.Attribute):
                            bname = base.attr
                        if bname and "Widget" in bname:
                            has_widget_classes = True
                            break
                if has_widget_classes:
                    break
        except Exception:
            pass

        if has_widget_classes:
            # Check if ready() imports widgets
            ready_imports_widgets = False
            for node in config_class.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "ready":
                    for child in ast.walk(node):
                        if isinstance(child, ast.ImportFrom):
                            # `from .widgets import ...` or `from . import widgets`
                            if child.module and "widgets" in child.module:
                                ready_imports_widgets = True
                            elif child.module is None:
                                for alias in child.names:
                                    if alias.name == "widgets":
                                        ready_imports_widgets = True
                        elif isinstance(child, ast.Import):
                            for alias in child.names:
                                if "widgets" in alias.name:
                                    ready_imports_widgets = True
            if ready_imports_widgets:
                results.append(CheckResult("ready_widgets", Severity.PASS, "ready() imports widgets module"))
            else:
                results.append(
                    CheckResult(
                        "ready_widgets",
                        Severity.WARNING,
                        "widgets.py has widget classes but ready() doesn't import widgets (widgets won't register)",
                    )
                )

    # Check __version__ or importlib.metadata at module level
    has_version_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "version":
            for alias in node.names:
                if alias.name == "__version__":
                    has_version_import = True

    if "__version__" in top_assignments:
        results.append(CheckResult("__version__", Severity.PASS, f'__version__ = "{top_assignments["__version__"]}"'))
    elif has_version_import:
        results.append(CheckResult("__version__", Severity.PASS, "__version__ imported from .version module"))
    elif "version" in attrs and attrs["version"] == "__dynamic_version__":
        results.append(CheckResult("__version__", Severity.PASS, "Version via importlib.metadata (modern pattern)"))
    else:
        results.append(CheckResult("__version__", Severity.WARNING, "__version__ not found at module level"))

    return cat

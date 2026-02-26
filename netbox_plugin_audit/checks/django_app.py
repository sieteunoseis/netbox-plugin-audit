"""Check Django app structure and NetBox plugin patterns."""

import ast
import os

from . import CategoryResult, CheckResult, Severity


def _has_django_models(filepath: str) -> bool:
    """Check if models.py defines any Django model classes."""
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read())
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    name = None
                    if isinstance(base, ast.Name):
                        name = base.id
                    elif isinstance(base, ast.Attribute):
                        name = base.attr
                    if name and "Model" in name:
                        return True
        return False
    except Exception:
        return False


def _has_django_views(filepath: str) -> bool:
    """Check if views.py defines any view classes or functions."""
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read())
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                return True
        return False
    except Exception:
        return False


def check_django_app(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Validate Django app structure follows NetBox plugin conventions."""
    cat = CategoryResult(name="Django Structure", icon="D")
    results = cat.results

    if not pkg_dir:
        results.append(CheckResult("package", Severity.ERROR, "No package directory to check"))
        return cat

    pkg_path = os.path.join(plugin_path, pkg_dir)

    # --- Core Django files ---
    # urls.py
    urls_path = os.path.join(pkg_path, "urls.py")
    has_urls = os.path.isfile(urls_path)
    if has_urls:
        results.append(CheckResult("urls_py", Severity.PASS, "urls.py exists"))
    else:
        results.append(CheckResult("urls_py", Severity.INFO, "urls.py not found (OK if no custom views)"))

    # views.py or views/ directory
    views_path = os.path.join(pkg_path, "views.py")
    views_dir = os.path.join(pkg_path, "views")
    has_views = os.path.isfile(views_path) or os.path.isdir(views_dir)
    if has_views:
        results.append(CheckResult("views_py", Severity.PASS, "views.py exists"))
    else:
        results.append(CheckResult("views_py", Severity.INFO, "views.py not found (OK if no custom views)"))

    # models.py or models/ directory
    models_path = os.path.join(pkg_path, "models.py")
    models_dir = os.path.join(pkg_path, "models")
    has_models_file = os.path.isfile(models_path) or os.path.isdir(models_dir)
    has_models = False
    if os.path.isfile(models_path):
        has_models = _has_django_models(models_path)
    elif os.path.isdir(models_dir):
        # Check any .py file in models/ for model classes
        for f in os.listdir(models_dir):
            if f.endswith(".py") and f != "__init__.py":
                if _has_django_models(os.path.join(models_dir, f)):
                    has_models = True
                    break

    if has_models_file:
        results.append(CheckResult("models_py", Severity.PASS, "models.py exists"))
    else:
        results.append(CheckResult("models_py", Severity.INFO, "models.py not found (OK if no custom models)"))

    # --- Migrations ---
    migrations_dir = os.path.join(pkg_path, "migrations")
    if has_models:
        if os.path.isdir(migrations_dir):
            init_path = os.path.join(migrations_dir, "__init__.py")
            if os.path.isfile(init_path):
                results.append(CheckResult("migrations_init", Severity.PASS, "migrations/__init__.py exists"))
            else:
                results.append(
                    CheckResult("migrations_init", Severity.ERROR, "migrations/__init__.py missing (required)")
                )
            # Count migration files
            migration_files = [f for f in os.listdir(migrations_dir) if f.endswith(".py") and f != "__init__.py"]
            if migration_files:
                results.append(
                    CheckResult("migrations_count", Severity.PASS, f"{len(migration_files)} migration file(s) found")
                )
            else:
                results.append(
                    CheckResult(
                        "migrations_count", Severity.WARNING, "No migration files (models defined but no migrations)"
                    )
                )
        else:
            results.append(
                CheckResult(
                    "migrations_dir", Severity.WARNING, "migrations/ not found (models defined but no migrations)"
                )
            )
    elif os.path.isdir(migrations_dir):
        results.append(CheckResult("migrations_dir", Severity.PASS, "migrations/ directory exists"))

    # --- NetBox plugin files ---
    # navigation.py
    nav_path = os.path.join(pkg_path, "navigation.py")
    if os.path.isfile(nav_path):
        results.append(CheckResult("navigation_py", Severity.PASS, "navigation.py exists"))
    else:
        if has_views:
            results.append(
                CheckResult("navigation_py", Severity.INFO, "navigation.py not found (views exist, consider adding)")
            )
        else:
            results.append(CheckResult("navigation_py", Severity.INFO, "navigation.py not found"))

    # tables.py
    tables_path = os.path.join(pkg_path, "tables.py")
    if os.path.isfile(tables_path):
        results.append(CheckResult("tables_py", Severity.PASS, "tables.py exists"))
    elif has_models:
        results.append(CheckResult("tables_py", Severity.INFO, "tables.py not found (models exist, consider adding)"))

    # filtersets.py
    filtersets_path = os.path.join(pkg_path, "filtersets.py")
    if os.path.isfile(filtersets_path):
        results.append(CheckResult("filtersets_py", Severity.PASS, "filtersets.py exists"))
    elif has_models:
        results.append(
            CheckResult("filtersets_py", Severity.INFO, "filtersets.py not found (models exist, consider adding)")
        )

    # forms.py
    forms_path = os.path.join(pkg_path, "forms.py")
    if os.path.isfile(forms_path):
        results.append(CheckResult("forms_py", Severity.PASS, "forms.py exists"))
    elif has_models and has_views:
        results.append(
            CheckResult("forms_py", Severity.INFO, "forms.py not found (models+views exist, consider adding)")
        )

    # template_content.py
    tc_path = os.path.join(pkg_path, "template_content.py")
    if os.path.isfile(tc_path):
        results.append(CheckResult("template_content_py", Severity.PASS, "template_content.py exists"))

    # graphql.py
    gql_path = os.path.join(pkg_path, "graphql.py")
    if os.path.isfile(gql_path):
        results.append(CheckResult("graphql_py", Severity.PASS, "graphql.py exists"))

    # --- API structure ---
    api_dir = os.path.join(pkg_path, "api")
    if os.path.isdir(api_dir):
        results.append(CheckResult("api_dir", Severity.PASS, "api/ directory exists"))

        api_files = {
            "__init__.py": ("api_init", Severity.WARNING),
            "serializers.py": ("api_serializers", Severity.WARNING),
            "urls.py": ("api_urls", Severity.WARNING),
            "views.py": ("api_views", Severity.WARNING),
        }
        for fname, (check_name, sev) in api_files.items():
            fpath = os.path.join(api_dir, fname)
            if os.path.isfile(fpath):
                results.append(CheckResult(check_name, Severity.PASS, f"api/{fname} exists"))
            else:
                results.append(CheckResult(check_name, sev, f"api/{fname} missing"))
    elif has_models:
        results.append(
            CheckResult("api_dir", Severity.INFO, "api/ directory not found (models exist, consider adding)")
        )

    return cat

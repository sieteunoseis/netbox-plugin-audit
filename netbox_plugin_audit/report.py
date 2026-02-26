"""Report formatting for audit results."""

import json

from .checks import Severity

# Terminal colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"

SEVERITY_SYMBOLS = {
    Severity.PASS: f"{GREEN}PASS{RESET}",
    Severity.INFO: f"{CYAN}INFO{RESET}",
    Severity.WARNING: f"{YELLOW}WARN{RESET}",
    Severity.ERROR: f"{RED}FAIL{RESET}",
}

CATEGORY_ICONS = {
    "F": "📁",
    "C": "⚙️ ",
    "P": "📦",
    "V": "🔢",
    "L": "📋",
    "R": "📖",
    "W": "🔧",
    "D": "🧩",
    "Q": "🔍",
    "S": "🔒",
    "B": "🏗️ ",
    "T": "🏅",
}


def format_terminal(result: dict) -> str:
    """Format audit result for terminal output with colors."""
    lines = []

    name = result["plugin_name"]
    version = result.get("version", "unknown")

    # Header
    lines.append("")
    lines.append(f"{BOLD}{'═' * 58}{RESET}")
    lines.append(f"{BOLD}  NetBox Plugin Audit Report{RESET}")
    lines.append(f"{BOLD}  Plugin: {name} (v{version}){RESET}")
    lines.append(f"{BOLD}{'═' * 58}{RESET}")
    lines.append("")

    if result.get("error"):
        lines.append(f"  {RED}ERROR: {result['error']}{RESET}")
        lines.append("")
        return "\n".join(lines)

    # Categories
    for cat in result["categories"]:
        icon = CATEGORY_ICONS.get(cat.icon, "📌")
        score = f"{cat.passed}/{cat.total}"

        if cat.errors > 0:
            score_color = RED
        elif cat.warnings > 0:
            score_color = YELLOW
        else:
            score_color = GREEN

        header = f"{icon} {cat.name}"
        lines.append(f"  {BOLD}{header:<45}{RESET} {score_color}{score}{RESET}")

        for check in cat.results:
            symbol = SEVERITY_SYMBOLS[check.severity]
            lines.append(f"    {symbol}  {check.message}")

        lines.append("")

    # Summary
    summary = result["summary"]
    total = summary["total"]
    passed = summary["passed"]
    pct = round(passed / total * 100) if total > 0 else 0

    if pct >= 90:
        pct_color = GREEN
    elif pct >= 70:
        pct_color = YELLOW
    else:
        pct_color = RED

    lines.append(f"  {BOLD}{'─' * 58}{RESET}")
    lines.append(f"  {BOLD}Summary:{RESET} {pct_color}{passed}/{total} checks passed ({pct}%){RESET}")
    lines.append(
        f"    {RED}Errors: {summary['errors']}{RESET}"
        f" | {YELLOW}Warnings: {summary['warnings']}{RESET}"
        f" | {CYAN}Info: {summary['infos']}{RESET}"
    )
    lines.append("")

    return "\n".join(lines)


def format_json(result: dict) -> str:
    """Format audit result as JSON."""
    output = {
        "plugin_name": result["plugin_name"],
        "version": result.get("version"),
        "summary": result["summary"],
        "categories": [],
    }

    if result.get("error"):
        output["error"] = result["error"]

    for cat in result.get("categories", []):
        cat_data = {
            "name": cat.name,
            "passed": cat.passed,
            "total": cat.total,
            "checks": [],
        }
        for check in cat.results:
            cat_data["checks"].append(
                {
                    "name": check.name,
                    "severity": check.severity.value,
                    "message": check.message,
                }
            )
        output["categories"].append(cat_data)

    return json.dumps(output, indent=2)


def format_markdown(result: dict) -> str:
    """Format audit result as Markdown."""
    lines = []

    name = result["plugin_name"]
    version = result.get("version", "unknown")

    lines.append(f"# NetBox Plugin Audit: {name} (v{version})")
    lines.append("")

    if result.get("error"):
        lines.append(f"**ERROR:** {result['error']}")
        lines.append("")
        return "\n".join(lines)

    # Summary table
    summary = result["summary"]
    total = summary["total"]
    passed = summary["passed"]
    pct = round(passed / total * 100) if total > 0 else 0

    lines.append(f"**Score: {passed}/{total} ({pct}%)**")
    lines.append(f"Errors: {summary['errors']} | Warnings: {summary['warnings']} | Info: {summary['infos']}")
    lines.append("")

    severity_md = {
        Severity.PASS: "✅",
        Severity.INFO: "ℹ️",
        Severity.WARNING: "⚠️",
        Severity.ERROR: "❌",
    }

    for cat in result["categories"]:
        lines.append(f"## {cat.name} ({cat.passed}/{cat.total})")
        lines.append("")
        for check in cat.results:
            icon = severity_md[check.severity]
            lines.append(f"- {icon} {check.message}")
        lines.append("")

    return "\n".join(lines)

"""CLI entrypoint for NetBox Plugin Audit."""

import argparse
import sys

from . import __version__
from .auditor import audit_plugin
from .report import format_json, format_markdown, format_terminal


def main():
    parser = argparse.ArgumentParser(
        prog="netbox-plugin-audit",
        description="Audit NetBox plugins for structure, metadata, and best practices",
    )
    parser.add_argument("source", help="Git URL or local path to the plugin")
    parser.add_argument(
        "--format",
        choices=["terminal", "json", "markdown"],
        default="terminal",
        help="Output format (default: terminal)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 on any warning or error",
    )
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip black/isort/flake8 checks",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip package build test",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    result = audit_plugin(
        source=args.source,
        skip_lint=args.skip_lint,
        skip_build=args.skip_build,
    )

    if args.format == "json":
        print(format_json(result))
    elif args.format == "markdown":
        print(format_markdown(result))
    else:
        print(format_terminal(result))

    # Exit code
    summary = result["summary"]
    if result.get("error"):
        sys.exit(1)
    elif args.strict and (summary["errors"] > 0 or summary["warnings"] > 0):
        sys.exit(1)
    elif summary["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

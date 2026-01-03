"""Command-line interface for pydocs."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .formatters.rich import RichFormatter
from .inspector import extract_source, inspect_path, resolve_dotted_path


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="pydocs",
        description="Interactive Python package documentation explorer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  pydocs json                    Overview of json package
  pydocs json.dumps              Details of dumps function
  pydocs json.JSONEncoder        Details of JSONEncoder class
  pydocs urllib.parse.urlparse --source   Show source code
  pydocs os.path --depth 3       Deeper tree view
  pydocs mypackage --private     Include private members
""",
    )

    # Positional argument: the target path
    parser.add_argument(
        "target",
        help="Python package, module, class, or function path (e.g., json.dumps)",
    )

    # Output mode flags (mutually exclusive)
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--source",
        "-s",
        action="store_true",
        help="Show source code only",
    )
    output_group.add_argument(
        "--doc",
        "-d",
        action="store_true",
        help="Show docstring only",
    )
    output_group.add_argument(
        "--signature",
        "-g",
        action="store_true",
        help="Show signature only",
    )

    # Filtering flags
    parser.add_argument(
        "--private",
        "-p",
        action="store_true",
        help="Include private members (starting with _)",
    )
    parser.add_argument(
        "--imported",
        "-i",
        action="store_true",
        help="Include members imported from other modules",
    )

    # Display options
    parser.add_argument(
        "--depth",
        "-n",
        type=int,
        default=2,
        metavar="N",
        help="Maximum depth for tree display (default: 2)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    # Additional options
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="%(prog)s 0.1.0",
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Perform inspection
    result = inspect_path(
        args.target,
        include_private=args.private,
        include_imported=args.imported,
    )

    if result.error:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1

    # Create formatter
    formatter = RichFormatter(
        no_color=args.no_color,
        max_depth=args.depth,
        show_imported=args.imported,
        show_private=args.private,
    )

    # Dispatch to appropriate output mode
    if args.source:
        formatter.print_source(result)
    elif args.doc:
        formatter.print_docstring(result)
    elif args.signature:
        formatter.print_signature(result)
    elif args.json:
        formatter.print_json(result)
    else:
        formatter.print_overview(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())

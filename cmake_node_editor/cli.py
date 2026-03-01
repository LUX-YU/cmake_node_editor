"""
CLI entry point for headless CMake node builds.

Usage::

    # Show project info (node list, IDs, edges, build order)
    cmake-node-cli info project.json

    # Full generate (configure + build + install) all nodes
    cmake-node-cli build project.json

    # Only configure, starting from node 3
    cmake-node-cli build project.json --stage configure --start 3

    # Build a specific range of nodes
    cmake-node-cli build project.json --stage build --start 2 --end 5

    # Only the first node in the range
    cmake-node-cli build project.json --stage install --start 1 --only-first

    # Quiet mode (errors only)
    cmake-node-cli build project.json -q
"""

from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cmake-node-cli",
        description="Headless CLI for CMake Node Editor — build projects without a GUI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- info ----
    p_info = sub.add_parser("info", help="Show project summary (nodes, edges, build order).")
    p_info.add_argument("project", help="Path to the project JSON file.")

    # ---- build ----
    p_build = sub.add_parser("build", help="Execute a build stage on the project.")
    p_build.add_argument("project", help="Path to the project JSON file.")
    p_build.add_argument(
        "--stage", "-s",
        choices=["configure", "build", "install", "all"],
        default="all",
        help="Which stage to run (default: all).",
    )
    p_build.add_argument(
        "--start", type=int, default=None, metavar="NODE_ID",
        help="Start from this node ID (inclusive).",
    )
    p_build.add_argument(
        "--end", type=int, default=None, metavar="NODE_ID",
        help="Stop after this node ID (inclusive).",
    )
    p_build.add_argument(
        "--only-first", action="store_true",
        help="Execute only the first node in the range.",
    )
    p_build.add_argument(
        "--no-vcvars", action="store_true",
        help="Skip loading Visual Studio environment (Windows only).",
    )
    p_build.add_argument(
        "-q", "--quiet", action="store_true",
        help="Suppress informational output; only print errors.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "info":
        from .services.headless_builder import project_info
        try:
            print(project_info(args.project))
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        return 0

    if args.command == "build":
        from .services.headless_builder import headless_build
        ok = headless_build(
            filepath=args.project,
            stage=args.stage,
            start_node_id=args.start,
            end_node_id=args.end,
            only_first=args.only_first,
            verbose=not args.quiet,
            load_vcvars=not args.no_vcvars,
        )
        return 0 if ok else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

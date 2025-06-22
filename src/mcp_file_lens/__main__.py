"""This module provides the entry point for running the MCP File Lens server."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .security import set_allowed_directory, set_debug_mode, set_gitignore_enabled
from .server import create_server


def main() -> None:
    """This function starts the MCP File Lens server to handle incoming requests.

    It requires: nothing special
    Side effects: starts an MCP server that listens for requests
    Commonly used by: command line invocation via 'python -m mcp_file_lens'
    Typical usage: called directly when the module is run
    """
    parser = argparse.ArgumentParser(
        description="MCP File Lens - A secure file access server for LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Security:
  The --allowed-dir argument restricts file access to a specific directory tree.
  This is REQUIRED for security - the server will only access files within this directory.

Examples:
  python -m mcp_file_lens --allowed-dir ./my_project
  python -m mcp_file_lens --allowed-dir /absolute/path/to/project
        """,
    )

    parser.add_argument(
        "--allowed-dir",
        type=str,
        required=True,
        help="Directory to allow file access (relative to current directory)",
    )

    gitignore_group = parser.add_mutually_exclusive_group()
    gitignore_group.add_argument(
        "--enable-gitignore",
        action="store_true",
        default=True,
        help="Enable gitignore filtering (default)",
    )
    gitignore_group.add_argument(
        "--disable-gitignore", action="store_true", help="Disable gitignore filtering"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging based on debug flag
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        # Suppress ALL logging including from FastMCP
        logging.basicConfig(level=logging.CRITICAL)
        # Disable specific loggers that might still output
        logging.getLogger("FastMCP").setLevel(logging.CRITICAL)
        logging.getLogger("fastmcp").setLevel(logging.CRITICAL)
        logging.getLogger("mcp").setLevel(logging.CRITICAL)
        # Disable root logger to be safe
        logging.getLogger().setLevel(logging.CRITICAL)

    logger = logging.getLogger(__name__)

    try:
        # Set up configuration
        if args.debug:
            logger.debug(f"Setting allowed directory: {args.allowed_dir}")

        set_allowed_directory(args.allowed_dir)

        # Configure gitignore
        gitignore_enabled = not args.disable_gitignore
        set_gitignore_enabled(gitignore_enabled)

        # Configure debug mode
        set_debug_mode(args.debug)

        if args.debug:
            # Security is now handled by the SecureFileSystem adapter
            logger.debug("Secure filesystem adapter configured")

            # Resolve and log the actual allowed path
            allowed_path = Path(args.allowed_dir).resolve()
            logger.debug(f"File access restricted to: {allowed_path}")
            logger.debug(
                f"Gitignore filtering: {'enabled' if gitignore_enabled else 'disabled'}"
            )
            logger.debug("Starting MCP File Lens server...")
        server = create_server()
        server.run()
    except ValueError as e:
        if args.debug:
            logger.error(f"Invalid allowed directory: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        if args.debug:
            logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        if args.debug:
            logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""This module implements the MCP File Lens server with file system navigation tools."""

import logging
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from .security import fs

logger = logging.getLogger(__name__)

# Initialize the FastMCP server
mcp: FastMCP[Any] = FastMCP("mcp-file-lens")


def _list_directory_recursive(
    dir_path: str, relative_to: Path | None = None
) -> list[str]:
    """This function recursively lists all files and directories in a given path.

    It requires: a valid directory path string
    Side effects: accesses filesystem through secure adapter
    Commonly used by: list_dir function
    Typical usage: files = _list_directory_recursive('.')

    Args:
        dir_path: Directory path string to list recursively
        relative_to: Path to make results relative to (default: resolved dir_path)

    Returns:
        List of formatted strings in ls -la style
    """
    if relative_to is None:
        relative_to = Path(dir_path).resolve()

    result = []

    try:
        for item in sorted(fs.rglob(dir_path)):
            if fs.is_file(item):
                # Get relative path from the base directory
                try:
                    rel_path = item.relative_to(relative_to)
                    size = fs.stat(item).st_size
                    result.append(f"{size:>10} {rel_path}")
                except ValueError:
                    # Skip if can't make relative
                    continue

    except (OSError, PermissionError) as e:
        logger.debug(f"Skipping directory due to permission error: {e}")

    return result


def _list_directory_simple(dir_path: str) -> list[str]:
    """This function lists directory contents in a simple ls -la format.

    It requires: a valid directory path string
    Side effects: accesses filesystem through secure adapter
    Commonly used by: list_dir function
    Typical usage: files = _list_directory_simple('.')

    Args:
        dir_path: Directory path string to list

    Returns:
        List of formatted strings in ls -la style
    """
    result = []

    try:
        for item in sorted(fs.iterdir(dir_path)):
            if fs.is_dir(item):
                result.append(f"{'':>10} {item.name}/")
            else:
                size = fs.stat(item).st_size
                result.append(f"{size:>10} {item.name}")

    except (OSError, PermissionError) as e:
        logger.debug(f"Error listing directory: {e}")

    return result


@mcp.tool()
def list_dir(path: str = ".", recursive: bool = False) -> str:
    """List directory contents in ls -la format - ideal for exploring codebases with minimal context usage.

    PURPOSE: Navigate file structures efficiently without consuming context on file contents.
    USE WHEN: You need to explore a codebase structure, find specific files, or understand project organization.
    COMBINES WITH: Use before read_file_grep to find files, or with language servers for project navigation.

    BENEFITS FOR LLMs:
    - Preserves context by showing only names/types, not file contents
    - Helps locate error-related files when debugging user issues
    - Enables systematic codebase exploration without noise
    - Plain text format mimics familiar ls output

    Args:
        path: Directory path to list (default: current directory)
        recursive: If True, recursively list all files (default: False)

    Returns:
        Plain text directory listing in ls -la format
    """
    try:
        if not fs.exists(path):
            return f"Error: Path does not exist: {path}"

        if not fs.is_dir(path):
            return f"Error: Path is not a directory: {path}"

        if recursive:
            items = _list_directory_recursive(path)
        else:
            items = _list_directory_simple(path)

        if not items:
            return f"Directory {path} is empty"

        return "\n".join(items)

    except PermissionError as e:
        logger.debug(f"Permission denied listing directory {path}: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.debug(f"Error listing directory {path}: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
def read_file(path: str, lineno: bool = True) -> str:
    """Read ENTIRE file contents - use when you need complete context of a small file.

    PURPOSE: Get full file contents when you need to see everything.
    USE WHEN: File is small, you need full context, or other tools require complete file view.
    AVOID WHEN: File is large or you only need specific parts - use read_file_grep or read_file_range instead.

    CONTEXT OPTIMIZATION:
    - Line numbers included by default (lineno=True) for easy reference
    - For large files, consider read_file_range to get specific sections
    - For pattern search, use read_file_grep to minimize noise
    - Plain text format mimics familiar cat -n output

    Args:
        path: File path to read completely
        lineno: Include line numbers like 'cat -n' format (default: True)

    Returns:
        Plain text file contents with optional line numbers
    """
    try:
        if not fs.exists(path):
            return f"Error: File does not exist: {path}"

        if not fs.is_file(path):
            return f"Error: Path is not a file: {path}"

        content = fs.read_text(path)
        lines = content.splitlines()

        if lineno:
            # Format content with line numbers like cat -n
            formatted_lines = []
            for i, line in enumerate(lines, 1):
                formatted_lines.append(f"{i:>6}\t{line}")
            return "\n".join(formatted_lines)
        else:
            return content

    except PermissionError as e:
        logger.debug(f"Permission denied reading file {path}: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.debug(f"Error reading file {path}: {e}")
        return f"Error: {str(e)}"


def _grep_file(
    file_path: str | Path,
    search_string: str,
    before: int = 0,
    after: int = 0,
    lineno: bool = True,
    filename: bool = False,
) -> list[str]:
    """This function searches for a string in a file and returns matching lines with context.

    It requires: a valid file path and search string
    Side effects: accesses filesystem through secure adapter
    Commonly used by: read_file_grep and read_files_grep functions
    Typical usage: matches = _grep_file('file.py', 'def', context=2)

    Args:
        file_path: File path (string or Path) to search in
        search_string: Text to find (case-sensitive)
        before: Lines to include before each match
        after: Lines to include after each match
        lineno: Include line numbers in output
        filename: Include filename prefix in output

    Returns:
        List of formatted strings matching grep output
    """
    try:
        content = fs.read_text(file_path)
        lines = content.splitlines()

        # Find matching lines with their indices
        match_indices = []
        for i, line in enumerate(lines):
            if search_string in line:
                match_indices.append(i)

        if not match_indices:
            return []

        # Build result with context lines
        result_lines: list[str] = []
        included_indices: set[int] = set()

        for match_idx in match_indices:
            # Calculate range with before/after context
            start_idx = max(0, match_idx - before)
            end_idx = min(len(lines), match_idx + after + 1)

            # Add separator if there's a gap from previous group
            if (
                result_lines
                and included_indices
                and min(range(start_idx, end_idx)) > max(included_indices) + 1
            ):
                result_lines.append("--")

            # Add lines in range
            for idx in range(start_idx, end_idx):
                if idx not in included_indices:
                    line_content = lines[idx]

                    # Build prefix
                    prefix_parts = []
                    if filename:
                        # Use relative path from current working directory
                        try:
                            file_path_obj = (
                                Path(file_path)
                                if isinstance(file_path, str)
                                else file_path
                            )
                            rel_path = file_path_obj.relative_to(Path.cwd())
                            prefix_parts.append(str(rel_path))
                        except ValueError:
                            prefix_parts.append(str(file_path))
                    if lineno:
                        prefix_parts.append(str(idx + 1))

                    if prefix_parts:
                        formatted_line = ":".join(prefix_parts) + ":" + line_content
                    else:
                        formatted_line = line_content

                    result_lines.append(formatted_line)
                    included_indices.add(idx)

        return result_lines

    except PermissionError as e:
        logger.debug(f"Permission denied reading file {file_path}: {e}")
        return []
    except Exception as e:
        logger.debug(f"Error reading file {file_path}: {e}")
        return []


@mcp.tool()
def read_file_grep(
    path: str,
    search_string: str,
    before: int = 0,
    after: int = 0,
    context: int | None = None,
    lineno: bool = True,
) -> str:
    """Search file for specific strings WITH context - ideal for finding and understanding code sections with MINIMAL noise.

    PURPOSE: Extract only relevant lines from files, preserving context window for important analysis.
    USE WHEN:
    - Debugging: Find error locations from user stack traces
    - Code search: Locate function definitions, variable usage, imports
    - Understanding: Get code context around specific patterns

    SYNERGY WITH OTHER TOOLS:
    - After list_dir: Search within discovered files
    - With language servers: Find text patterns while LSP handles symbols
    - For error debugging: Locate exact error lines from compiler output

    CONTEXT OPTIMIZATION:
    - Returns ONLY matching lines plus requested context
    - Dramatically reduces token usage vs reading entire files
    - Use context=2 or context=3 for understanding code flow
    - Use before/after for asymmetric context needs
    - Plain text format mimics familiar grep -n output

    Args:
        path: File to search within
        search_string: Text to find (case-sensitive)
        before: Lines to include before each match (like grep -B)
        after: Lines to include after each match (like grep -A)
        context: Sets both before AND after (like grep -C)
        lineno: Include line numbers (default: True)

    Returns:
        Plain text grep-style output with matching lines and context
    """
    try:
        if not fs.exists(path):
            return f"Error: File does not exist: {path}"

        if not fs.is_file(path):
            return f"Error: Path is not a file: {path}"

        if not search_string:
            return "Error: Search string cannot be empty"

        # Handle context parameter
        if context is not None:
            before = after = context

        result_lines = _grep_file(
            path, search_string, before, after, lineno, filename=False
        )

        if not result_lines:
            return f"No matches found for '{search_string}' in {path}"

        return "\n".join(result_lines)

    except PermissionError as e:
        logger.debug(f"Permission denied filtering file {path}: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.debug(f"Error filtering file {path}: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
def read_files_grep(
    path: str = ".",
    search_string: str = "",
    before: int = 0,
    after: int = 0,
    context: int | None = None,
    lineno: bool = True,
    filename: bool = True,
) -> str:
    """Search recursively through all files in a directory for specific strings WITH context.

    PURPOSE: Find patterns across multiple files in a directory tree, combining list_dir and read_file_grep functionality.
    USE WHEN:
    - Searching for function definitions across a codebase
    - Finding all usages of a variable or import across files
    - Debugging issues that span multiple files
    - Understanding code patterns across a project

    SYNERGY WITH OTHER TOOLS:
    - Combines list_dir recursive functionality with read_file_grep search
    - Use with language servers for comprehensive code analysis
    - Perfect for cross-file refactoring and analysis

    CONTEXT OPTIMIZATION:
    - Returns ONLY matching lines plus requested context from all files
    - Shows filename for each match to understand file origins
    - Plain text format mimics familiar grep -r output
    - Dramatically more efficient than reading entire files individually

    Args:
        path: Directory to search recursively (default: current directory)
        search_string: Text to find (case-sensitive)
        before: Lines to include before each match (like grep -B)
        after: Lines to include after each match (like grep -A)
        context: Sets both before AND after (like grep -C)
        lineno: Include line numbers (default: True)
        filename: Include filename prefix (default: True)

    Returns:
        Plain text grep-style output with matches from all files, including filenames
    """
    try:
        if not fs.exists(path):
            return f"Error: Path does not exist: {path}"

        if not fs.is_dir(path):
            return f"Error: Path is not a directory: {path}"

        if not search_string:
            return "Error: Search string cannot be empty"

        # Handle context parameter
        if context is not None:
            before = after = context

        # Get all files recursively using our existing function
        all_results = []
        file_count = 0
        match_count = 0

        try:
            for file_path in sorted(fs.rglob(path)):
                if fs.is_file(file_path):
                    file_count += 1

                    result_lines = _grep_file(
                        file_path, search_string, before, after, lineno, filename
                    )

                    if result_lines:
                        match_count += len(
                            [line for line in result_lines if search_string in line]
                        )
                        all_results.extend(result_lines)
                        if len(all_results) > 0 and all_results[-1] != "--":
                            all_results.append("--")  # Separator between files

        except (OSError, PermissionError) as e:
            logger.debug(f"Permission error during recursive search: {e}")

        # Remove trailing separator
        if all_results and all_results[-1] == "--":
            all_results.pop()

        if not all_results:
            return f"No matches found for '{search_string}' in {file_count} files under {path}"

        summary = f"Found matches in {len([r for r in all_results if r != '--'])} lines across {path}\n--\n"
        return summary + "\n".join(all_results)

    except PermissionError as e:
        logger.debug(f"Permission denied searching files in {path}: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.debug(f"Error searching files in {path}: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
def read_file_range(
    path: str, start_line: int, end_line: int, lineno: bool = True
) -> str:
    """Extract SPECIFIC line range from files - perfect for examining error locations or specific functions.

    PURPOSE: Read only a specific line range, ideal for focusing on error locations or particular code sections.
    USE WHEN:
    - Compiler/runtime errors give specific line numbers
    - You need to examine specific functions/classes
    - Following cross-references from other tools
    - Minimizing context usage in large files

    PERFECT FOR ERROR DEBUGGING:
    - User provides error "at line 142" -> use start_line=140, end_line=145 for context
    - Stack trace shows location -> focus on specific line range
    - Reviewing specific functions after grep/search

    SYNERGY:
    - After read_file_grep: Get expanded context around matches
    - With language servers: Read specific symbol definitions
    - For code review: Focus on changed sections only

    Args:
        path: File to read from
        start_line: Start line number (1-indexed, inclusive)
        end_line: End line number (1-indexed, inclusive)
        lineno: Include line numbers (default: True)

    Example:
        read_file_range("main.py", 10, 20)

    Returns:
        Plain text output with only requested line range
    """
    try:
        if not fs.exists(path):
            return f"Error: File does not exist: {path}"

        if not fs.is_file(path):
            return f"Error: Path is not a file: {path}"

        # Validate range
        if start_line < 1:
            return f"Error: Start line must be >= 1, got {start_line}"
        if end_line < start_line:
            return f"Error: End line must be >= start line, got range ({start_line}, {end_line})"

        content = fs.read_text(path)
        lines = content.splitlines()

        selected_lines = []

        # Adjust for 0-based indexing
        start_idx = start_line - 1
        end_idx = min(end_line, len(lines))

        for i in range(start_idx, end_idx):
            if i < len(lines):
                line_content = lines[i]
                if lineno:
                    line_content = f"{i + 1}:{line_content}"
                selected_lines.append(line_content)

        if not selected_lines:
            return f"No lines found in specified ranges for {path}"

        return "\n".join(selected_lines)

    except PermissionError as e:
        logger.debug(f"Permission denied reading file range {path}: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.debug(f"Error reading file range {path}: {e}")
        return f"Error: {str(e)}"


def create_server() -> FastMCP[Any]:
    """This function creates and configures the MCP File Lens server to handle requests.

    It requires: nothing special
    Side effects: none
    Commonly used by: __main__.main
    Typical usage: server = create_server()
    """
    # The result from this function goes to __main__.main
    return mcp

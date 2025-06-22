# mcp-file-lens

An MCP (Model Context Protocol) server that provides a flexible "lens" into your directory structure and files, enabling LLM clients to efficiently navigate and understand codebases with minimal noise.

## Overview

`mcp-file-lens` is a Python-based MCP server designed to give LLMs targeted access to file systems. Rather than reading entire file contents indiscriminately, it provides surgical tools to inspect exactly what's needed, preserving context window and improving comprehension.

This server is designed to work alongside other MCP servers like Language Protocol Servers (LPS), providing complementary file navigation capabilities while the LPS handles language-specific operations like symbol resolution, type checking, and refactoring.

## Features

### Security
- **Directory Restriction**: All file access is restricted to a specified directory tree via `--allowed-dir`
- **Secure Filesystem Adapter**: All MCP tools use a secure filesystem adapter that validates every path
- **Gitignore Filtering**: Automatically respects .gitignore patterns to avoid accessing ignored files
- **Binary File Detection**: Automatically skips binary files to prevent encoding errors
- **Targeted Security**: Security checks only apply to MCP tool operations, not system imports or libraries
- **No Escape**: Prevents directory traversal attacks and access to system files

### Core Functionality
- **Directory Listing** (`list_dir`): Navigate directory structures efficiently with optional recursive mode
- **File Content Retrieval** (`read_file`): Read complete file contents with optional line numbers
- **Single File Search** (`read_file_grep`): Find lines containing specific strings with context (like grep -A/-B/-C)
- **Multi-File Search** (`read_files_grep`): Recursively search across all files in a directory tree
- **Range Selection** (`read_file_range`): Extract a specific line range from files
- **Intelligent Filtering**: Automatically filters out binary files, respects gitignore patterns, and handles encoding issues gracefully

### Benefits
- **Efficient Context Usage**: Only read what's necessary
- **Noise Reduction**: Filter out irrelevant content, binary files, and gitignored files
- **Flexible Navigation**: Walk through codebases intelligently
- **Maximum Attention**: Focus on relevant code sections
- **Robust Error Handling**: Gracefully handles encoding issues and permission errors
- **Security First**: File access restricted to specified directory only
- **Plain Text Output**: All tools return plain text (not JSON) for optimal LLM parsing
- **Familiar Formats**: Output mimics standard Unix tools (ls, cat, grep)
- **Silent Operation**: No logging noise unless debug mode is enabled

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-file-lens.git
cd mcp-file-lens

# Install with pip (recommended)
pip install -e .
```

## Usage

### As an MCP Server

```bash
# Start the server with a specific allowed directory
python -m mcp_file_lens --allowed-dir ./my_project

# Or with an absolute path
python -m mcp_file_lens --allowed-dir /absolute/path/to/project

# Enable debug logging
python -m mcp_file_lens --allowed-dir ./my_project --debug

# Disable gitignore filtering (not recommended)
python -m mcp_file_lens --allowed-dir ./my_project --disable-gitignore
```

**Security Note**: The `--allowed-dir` argument is REQUIRED and restricts file access to only the specified directory tree. This prevents the LLM from accessing files outside your project.

### Configuration

Add to your MCP client configuration:

```json
{
  "servers": {
    "mcp-file-lens": {
      "command": "python",
      "args": ["-m", "mcp_file_lens", "--allowed-dir", "./my_project"],
      "env": {}
    }
  }
}
```

### Debug Configuration

For development or troubleshooting, enable debug mode:

```json
{
  "servers": {
    "mcp-file-lens": {
      "command": "python",
      "args": ["-m", "mcp_file_lens", "--allowed-dir", "./my_project", "--debug"],
      "env": {}
    }
  }
}
```

### Working with Other MCP Servers

`mcp-file-lens` is designed to complement other MCP servers. For example, when used alongside a Language Protocol Server:

```json
{
  "servers": {
    "mcp-file-lens": {
      "command": "python",
      "args": ["-m", "mcp_file_lens", "--allowed-dir", "./my_project"],
      "env": {}
    },
    "typescript-lps": {
      "command": "typescript-language-server",
      "args": ["--stdio"],
      "env": {}
    }
  }
}
```

This allows LLMs to:
1. Use `mcp-file-lens` for efficient file navigation and content inspection
2. Use the LPS for language-specific features like go-to-definition, find-references, etc.

## Tool APIs

### `list_dir(path: str = ".", recursive: bool = False)`
Lists the contents of a directory in ls -la format. Automatically filters out gitignored files and binary files.

**Parameters:**
- `path`: Directory path to list (default: current directory)
- `recursive`: If True, recursively list all files (default: False)

**Returns:** Plain text directory listing with file sizes and names (filtered by gitignore and excluding binary files)

**Filtering:** Respects .gitignore patterns and excludes binary files for cleaner output.

**Example Output:**
```
      2494 pyproject.toml
      6420 README.md
           src/
```

### `read_file(path: str, lineno: bool = True)`
Reads the complete contents of a file in cat -n format. Automatically skips binary files and handles UTF-8 encoding issues gracefully.

**Parameters:**
- `path`: File path to read
- `lineno`: Include line numbers in output (default: True)

**Returns:** Plain text file content with optional line numbers

**Example Output:**
```
     1	#!/usr/bin/env python3
     2	"""Main module"""
     3
     4	import sys
```

### `read_file_grep(path: str, search_string: str, before: int = 0, after: int = 0, context: int | None = None, lineno: bool = True)`
Searches for lines containing a string with optional context in grep -n format.

**Parameters:**
- `path`: File path to search
- `search_string`: String to search for
- `before`: Lines to include before each match (like grep -B)
- `after`: Lines to include after each match (like grep -A)
- `context`: Sets both before and after (like grep -C)
- `lineno`: Include line numbers in output (default: True)

**Returns:** Plain text grep-style output with matching lines and context

**Example Output:**
```
15:def install_audit_hook() -> None:
16:    """Install an audit hook to monitor file operations."""
17:    def audit_hook(event: str, args: Tuple) -> None:
--
25:    if _allowed_dir is not None:
26:        sys.addaudithook(audit_hook)
```

### `read_files_grep(path: str = ".", search_string: str = "", before: int = 0, after: int = 0, context: int | None = None, lineno: bool = True, filename: bool = True)`
Recursively searches for patterns across all files in a directory tree. Automatically filters out binary files and gitignored files for cleaner results.

**Parameters:**
- `path`: Directory to search recursively (default: current directory)
- `search_string`: String to search for
- `before`: Lines to include before each match (like grep -B)
- `after`: Lines to include after each match (like grep -A)
- `context`: Sets both before and after (like grep -C)
- `lineno`: Include line numbers in output (default: True)
- `filename`: Include filename prefix in output (default: True)

**Returns:** Plain text grep -r style output with matches from all files

**Example Output:**
```
src/server.py:15:def install_audit_hook() -> None:
src/server.py:16:    """Install an audit hook to monitor file operations."""
--
tests/test_server.py:42:def test_install_audit_hook():
tests/test_server.py:43:    """Test audit hook installation."""
```

### `read_file_range(path: str, start_line: int, end_line: int, lineno: bool = True)`
Reads a specific line range from a file.

**Parameters:**
- `path`: File path to read
- `start_line`: Start line number (1-indexed, inclusive)
- `end_line`: End line number (1-indexed, inclusive)
- `lineno`: Include line numbers in output (default: True)

**Example:**
```python
# Read lines 10-20
read_file_range("/path/to/file.py", 10, 20)
```

**Returns:** Plain text with selected lines from the specified range

**Example Output:**
```
10:import logging
11:from pathlib import Path
12:from typing import Any
--
50:def validate_path(path: str) -> Tuple[bool, str]:
51:    """Validate if path is allowed."""
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

### Project Structure

```
mcp-file-lens/
├── src/
│   └── mcp_file_lens/
│       ├── __init__.py
│       ├── __main__.py
│       └── server.py
├── tests/
│   └── test_server.py
├── pyproject.toml
└── README.md
```

## Command Line Arguments

### Required Arguments

- `--allowed-dir PATH`: **REQUIRED** - Restricts file access to the specified directory tree. Can be relative or absolute path.

### Optional Arguments

- `--enable-gitignore`: Enable gitignore filtering (default behavior). Files matching patterns in .gitignore will be excluded from listings and searches.
- `--disable-gitignore`: Disable gitignore filtering. All files will be accessible regardless of .gitignore patterns.
- `--debug`: Enable debug logging. Shows detailed information about file operations, errors, and security checks.

### Filtering Behavior

**Gitignore Support:**
- Automatically detects and parses .gitignore files in the allowed directory
- Supports common gitignore patterns including wildcards (*), directory patterns (/), and negations
- Applies filtering to all directory listings and recursive file operations
- Enabled by default, can be disabled with `--disable-gitignore`

**Binary File Detection:**
- Automatically identifies and skips binary files during text operations
- Uses content-based detection (null bytes, non-text character ratios)
- Prevents UTF-8 decoding errors and reduces noise in search results
- Always enabled for file content operations

**Error Handling:**
- UTF-8 decoding errors are handled gracefully with fallback to error replacement
- Permission errors are logged only in debug mode to reduce noise
- Binary files are skipped silently to avoid encoding issues

### Security Considerations

The `--allowed-dir` argument implements targeted security through a filesystem adapter:

1. **Path Validation**: Every MCP tool operation validates paths through a secure filesystem adapter
2. **No Traversal**: Prevents `../` and other directory traversal attempts
3. **Targeted Scope**: Security only applies to MCP file operations, not Python imports or library loading
4. **Absolute Resolution**: All paths are resolved to absolute paths before validation

This ensures that the LLM can only access files within your designated project directory, protecting your system files and other sensitive data, while allowing normal Python operations to function unimpeded.

## Requirements

- Python 3.12+
- FastMCP for MCP protocol implementation

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

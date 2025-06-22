"""Security module for enforcing file access restrictions."""

import os
import re
from pathlib import Path

# Global variables for configuration
_allowed_dir: Path | None = None
_gitignore_enabled: bool = True
_debug_mode: bool = False
_gitignore_patterns: list[str] | None = None


def set_allowed_directory(path: str) -> None:
    """Set the allowed directory for file operations.

    Args:
        path: Directory path relative to current working directory
    """
    global _allowed_dir, _gitignore_patterns
    _allowed_dir = Path(path).resolve()

    if not _allowed_dir.exists():
        raise ValueError(f"Allowed directory does not exist: {path}")

    if not _allowed_dir.is_dir():
        raise ValueError(f"Allowed path is not a directory: {path}")

    # Load gitignore patterns when setting directory
    _gitignore_patterns = _load_gitignore_patterns()


def set_gitignore_enabled(enabled: bool) -> None:
    """Enable or disable gitignore filtering.

    Args:
        enabled: True to enable gitignore filtering, False to disable
    """
    global _gitignore_enabled
    _gitignore_enabled = enabled


def set_debug_mode(enabled: bool) -> None:
    """Enable or disable debug mode.

    Args:
        enabled: True to enable debug mode, False to disable
    """
    global _debug_mode
    _debug_mode = enabled


def is_path_allowed(path: Path | str) -> bool:
    """Check if a path is within the allowed directory.

    Args:
        path: Path to check

    Returns:
        True if path is allowed, False otherwise
    """
    if _allowed_dir is None:
        # No restrictions if allowed_dir not set
        return True

    try:
        check_path = Path(path).resolve()
        # Check if the path is within allowed directory
        check_path.relative_to(_allowed_dir)
        return True
    except (ValueError, RuntimeError):
        # Path is outside allowed directory or doesn't exist
        return False


def _load_gitignore_patterns() -> list[str]:
    """Load gitignore patterns from .gitignore file in allowed directory.

    Returns:
        List of gitignore patterns, empty if no .gitignore file
    """
    if _allowed_dir is None:
        return []

    gitignore_path = _allowed_dir / ".gitignore"
    if not gitignore_path.exists():
        return []

    try:
        patterns = []
        with open(gitignore_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.append(line)
        return patterns
    except Exception:
        return []


def _is_gitignored(path: str | Path) -> bool:
    """Check if a path matches gitignore patterns.

    Args:
        path: Path to check

    Returns:
        True if path should be ignored, False otherwise
    """
    if not _gitignore_enabled or not _gitignore_patterns or _allowed_dir is None:
        return False

    try:
        # Get relative path from allowed directory
        path_obj = Path(path).resolve()
        rel_path = path_obj.relative_to(_allowed_dir)
        path_str = str(rel_path).replace("\\", "/")  # Normalize path separators

        for pattern in _gitignore_patterns:
            # Simple gitignore pattern matching (not full spec, but covers most cases)
            if _matches_gitignore_pattern(path_str, pattern):
                return True
        return False
    except (ValueError, Exception):
        return False


def _matches_gitignore_pattern(path: str, pattern: str) -> bool:
    """Check if a path matches a gitignore pattern.

    Args:
        path: Path string to check
        pattern: Gitignore pattern

    Returns:
        True if path matches pattern
    """
    # Handle directory patterns (ending with /)
    if pattern.endswith("/"):
        pattern = pattern[:-1]
        # Check if any parent directory matches
        parts = path.split("/")
        for i in range(len(parts)):
            if _simple_pattern_match("/".join(parts[: i + 1]), pattern):
                return True
        return False

    # Handle patterns starting with /
    if pattern.startswith("/"):
        pattern = pattern[1:]
        return _simple_pattern_match(path, pattern)

    # Check if pattern matches the full path or any suffix
    if _simple_pattern_match(path, pattern):
        return True

    # Check against path components
    parts = path.split("/")
    for i in range(len(parts)):
        if _simple_pattern_match("/".join(parts[i:]), pattern):
            return True
        if _simple_pattern_match(parts[i], pattern):
            return True

    return False


def _simple_pattern_match(text: str, pattern: str) -> bool:
    """Simple pattern matching with * wildcards.

    Args:
        text: Text to match against
        pattern: Pattern with * wildcards

    Returns:
        True if text matches pattern
    """
    # Convert gitignore pattern to regex
    regex_pattern = pattern.replace(".", "\\.")
    regex_pattern = regex_pattern.replace("*", "[^/]*")
    regex_pattern = "^" + regex_pattern + "$"

    try:
        return bool(re.match(regex_pattern, text))
    except re.error:
        return False


def _is_binary_file(path: str | Path) -> bool:
    """Check if a file is binary by reading its first chunk.

    Args:
        path: Path to file to check

    Returns:
        True if file appears to be binary, False otherwise
    """
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)  # Read first 1KB
            if not chunk:
                return False

            # Check for null bytes (common in binary files)
            if b"\x00" in chunk:
                return True

            # Check percentage of non-text characters
            non_text_chars = sum(
                1 for byte in chunk if byte < 32 and byte not in (9, 10, 13)
            )
            return bool(len(chunk) > 0 and non_text_chars / len(chunk) > 0.3)
    except (OSError, PermissionError):
        return True  # Assume binary if we can't read it


def validate_path(path: str) -> tuple[bool, str]:
    """Validate if a path is allowed and return appropriate error message.

    Args:
        path: Path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if _allowed_dir is None:
        # No restrictions
        return True, ""

    try:
        resolved_path = Path(path).resolve()

        # Special case: if path doesn't exist yet, check parent directory
        if not resolved_path.exists():
            parent = resolved_path.parent
            if parent.exists():
                parent.relative_to(_allowed_dir)
            else:
                return False, f"Parent directory does not exist: {parent}"
        else:
            # Path exists, check if it's within allowed directory
            resolved_path.relative_to(_allowed_dir)

        return True, ""
    except ValueError:
        # Path is outside allowed directory
        return False, f"Access denied: Path '{path}' is outside allowed directory"
    except Exception as e:
        return False, f"Path validation error: {e}"


class SecureFileSystem:
    """This class provides secure filesystem operations for MCP tools.

    It requires: an allowed directory to be set via set_allowed_directory
    Side effects: validates all paths before filesystem operations, applies gitignore filtering
    Commonly used by: all MCP tool functions
    Typical usage: fs = SecureFileSystem(); content = fs.read_text(path)
    """

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        """This function reads text from a file with security validation.

        It requires: a valid file path within allowed directory
        Side effects: reads file from disk
        Commonly used by: read_file, read_file_grep, read_files_grep functions
        Typical usage: content = fs.read_text('file.py')

        Args:
            path: File path to read
            encoding: Text encoding (default: utf-8)

        Returns:
            File contents as string
        """
        is_valid, error_msg = validate_path(str(path))
        if not is_valid:
            raise PermissionError(f"Access denied: {error_msg}")

        file_path = Path(path).resolve()

        # Skip binary files
        if _is_binary_file(file_path):
            raise PermissionError(f"Cannot read binary file: {path}")

        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            # Try with error handling for problematic files
            try:
                return file_path.read_text(encoding=encoding, errors="replace")
            except Exception as e:
                raise PermissionError(
                    f"Cannot decode file as {encoding}: {path}"
                ) from e

    def stat(self, path: str | Path) -> os.stat_result:
        """This function gets file statistics with security validation.

        It requires: a valid path within allowed directory
        Side effects: accesses filesystem metadata
        Commonly used by: list_dir function
        Typical usage: size = fs.stat('file.py').st_size

        Args:
            path: Path to get statistics for

        Returns:
            os.stat_result object
        """
        is_valid, error_msg = validate_path(str(path))
        if not is_valid:
            raise PermissionError(f"Access denied: {error_msg}")

        file_path = Path(path).resolve()
        return file_path.stat()

    def iterdir(self, path: str | Path) -> list[Path]:
        """This function lists directory contents with security validation.

        It requires: a valid directory path within allowed directory
        Side effects: accesses filesystem directory listing, applies gitignore filtering
        Commonly used by: list_dir function
        Typical usage: items = fs.iterdir('.')

        Args:
            path: Directory path to list

        Returns:
            List of Path objects in directory (filtered by gitignore if enabled)
        """
        is_valid, error_msg = validate_path(str(path))
        if not is_valid:
            raise PermissionError(f"Access denied: {error_msg}")

        dir_path = Path(path).resolve()
        items = list(dir_path.iterdir())

        # Apply gitignore filtering
        if _gitignore_enabled:
            filtered_items = []
            for item in items:
                if not _is_gitignored(item):
                    filtered_items.append(item)
            return filtered_items

        return items

    def rglob(self, path: str | Path, pattern: str = "*") -> list[Path]:
        """This function recursively globs files with security validation.

        It requires: a valid directory path within allowed directory
        Side effects: accesses filesystem recursively, applies gitignore filtering
        Commonly used by: list_dir and read_files_grep functions
        Typical usage: files = fs.rglob('.', '*.py')

        Args:
            path: Directory path to search recursively
            pattern: Glob pattern (default: '*')

        Returns:
            List of Path objects matching pattern (filtered by gitignore if enabled)
        """
        is_valid, error_msg = validate_path(str(path))
        if not is_valid:
            raise PermissionError(f"Access denied: {error_msg}")

        dir_path = Path(path).resolve()
        items = list(dir_path.rglob(pattern))

        # Apply gitignore filtering and skip binary files
        filtered_items = []
        for item in items:
            # Skip gitignored files
            if _gitignore_enabled and _is_gitignored(item):
                continue
            # Skip binary files for file operations
            if item.is_file() and _is_binary_file(item):
                continue
            filtered_items.append(item)
        return filtered_items

    def exists(self, path: str | Path) -> bool:
        """This function checks if a path exists with security validation.

        It requires: nothing special (validates path first)
        Side effects: accesses filesystem to check existence
        Commonly used by: all MCP tool functions
        Typical usage: if fs.exists('file.py'): ...

        Args:
            path: Path to check

        Returns:
            True if path exists and is allowed, False otherwise
        """
        is_valid, error_msg = validate_path(str(path))
        if not is_valid:
            return False

        file_path = Path(path).resolve()
        if not file_path.exists():
            return False

        # Check if path is gitignored
        return not (_gitignore_enabled and _is_gitignored(file_path))

    def is_file(self, path: str | Path) -> bool:
        """This function checks if a path is a file with security validation.

        It requires: a valid path within allowed directory
        Side effects: accesses filesystem metadata
        Commonly used by: all MCP tool functions
        Typical usage: if fs.is_file('file.py'): ...

        Args:
            path: Path to check

        Returns:
            True if path is a file and allowed, False otherwise
        """
        is_valid, error_msg = validate_path(str(path))
        if not is_valid:
            return False

        file_path = Path(path).resolve()
        if not file_path.is_file():
            return False

        # Check if file is gitignored
        return not (_gitignore_enabled and _is_gitignored(file_path))

    def is_dir(self, path: str | Path) -> bool:
        """This function checks if a path is a directory with security validation.

        It requires: a valid path within allowed directory
        Side effects: accesses filesystem metadata
        Commonly used by: list_dir function
        Typical usage: if fs.is_dir('src'): ...

        Args:
            path: Path to check

        Returns:
            True if path is a directory and allowed, False otherwise
        """
        is_valid, error_msg = validate_path(str(path))
        if not is_valid:
            return False

        file_path = Path(path).resolve()
        if not file_path.is_dir():
            return False

        # Check if directory is gitignored
        return not (_gitignore_enabled and _is_gitignored(file_path))


def install_audit_hook() -> None:
    """Install an audit hook to monitor file operations.

    This function is a stub for compatibility with tests.
    The actual security is handled by the SecureFileSystem class.
    """
    # This is a no-op function for compatibility
    pass


# Create a global instance for use by MCP tools
fs = SecureFileSystem()

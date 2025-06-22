"""This module contains tests for the MCP File Lens server functionality."""

from __future__ import annotations

from pathlib import Path

from mcp_file_lens import security, server


def get_function(tool):
    """Extract the actual function from a FastMCP tool wrapper."""
    return tool.fn if hasattr(tool, "fn") else tool


class TestListDirectory:
    """Tests for the list_dir tool."""

    def setup_method(self) -> None:
        """Reset security state before each test."""
        security._allowed_dir = None

    def test_list_empty_directory(self, tmp_path: Path) -> None:
        """This function tests listing an empty directory to verify basic functionality.

        It requires: a temporary directory
        Side effects: none
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        security.set_allowed_directory(str(tmp_path))
        result = get_function(server.list_dir)(str(tmp_path))

        assert "Error:" not in result
        assert "is empty" in result

    def test_list_directory_with_files(self, tmp_path: Path) -> None:
        """This function tests listing a directory with files to verify item detection.

        It requires: a temporary directory with test files
        Side effects: creates temporary files
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        # This section creates test files because we need to verify directory listing
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        security.set_allowed_directory(str(tmp_path))
        result = get_function(server.list_dir)(str(tmp_path))

        assert "Error:" not in result
        # Check that files are listed in the result
        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir/" in result

    def test_list_nonexistent_directory(self) -> None:
        """This function tests listing a nonexistent directory to verify error handling.

        It requires: nothing special
        Side effects: none
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        result = get_function(server.list_dir)("/nonexistent/path")

        assert "Error:" in result
        assert "does not exist" in result


class TestReadFile:
    """Tests for the read_file tool."""

    def setup_method(self) -> None:
        """Reset security state before each test."""
        security._allowed_dir = None

    def test_read_text_file(self, tmp_path: Path) -> None:
        """This function tests reading a text file to verify content retrieval.

        It requires: a temporary file with content
        Side effects: creates a temporary file
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        test_file = tmp_path / "test.txt"
        test_content = "Line 1\nLine 2\nLine 3"
        test_file.write_text(test_content)

        security.set_allowed_directory(str(tmp_path))
        result = get_function(server.read_file)(str(test_file))

        assert "Error:" not in result
        # With lineno=True (default), content should have line numbers
        expected_with_lineno = "     1\tLine 1\n     2\tLine 2\n     3\tLine 3"
        assert result == expected_with_lineno

    def test_read_text_file_without_lineno(self, tmp_path: Path) -> None:
        """This function tests reading a text file without line numbers.

        It requires: a temporary file with content
        Side effects: creates a temporary file
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        test_file = tmp_path / "test.txt"
        test_content = "Line 1\nLine 2\nLine 3"
        test_file.write_text(test_content)

        security.set_allowed_directory(str(tmp_path))
        result = get_function(server.read_file)(str(test_file), lineno=False)

        assert "Error:" not in result
        assert result == test_content

    def test_read_nonexistent_file(self) -> None:
        """This function tests reading a nonexistent file to verify error handling.

        It requires: nothing special
        Side effects: none
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        result = get_function(server.read_file)("/nonexistent/file.txt")

        assert "Error:" in result
        assert "does not exist" in result


class TestReadFileGrep:
    """Tests for the read_file_grep tool."""

    def setup_method(self) -> None:
        """Reset security state before each test."""
        security._allowed_dir = None

    def test_grep_matching_lines(self, tmp_path: Path) -> None:
        """This function tests filtering lines with matches to verify search functionality.

        It requires: a temporary file with searchable content
        Side effects: creates a temporary file
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        test_file = tmp_path / "test.py"
        test_content = """def function1():
    pass

def function2():
    return 42

class MyClass:
    def method1(self):
        pass"""
        test_file.write_text(test_content)

        security.set_allowed_directory(str(tmp_path))
        result = get_function(server.read_file_grep)(str(test_file), "def ")

        assert "Error:" not in result
        assert "1:def function1():" in result
        assert "4:def function2():" in result
        assert "8:    def method1(self):" in result

    def test_grep_with_context(self, tmp_path: Path) -> None:
        """This function tests grep with context lines.

        It requires: a temporary file with searchable content
        Side effects: creates a temporary file
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        test_file = tmp_path / "test.txt"
        test_content = """line 1
line 2
match line
line 4
line 5"""
        test_file.write_text(test_content)

        security.set_allowed_directory(str(tmp_path))
        result = get_function(server.read_file_grep)(str(test_file), "match", context=1)

        assert "Error:" not in result
        assert "2:line 2" in result
        assert "3:match line" in result
        assert "4:line 4" in result

    def test_grep_no_matches(self, tmp_path: Path) -> None:
        """This function tests filtering with no matches to verify empty result handling.

        It requires: a temporary file without matching content
        Side effects: creates a temporary file
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("No matches here")

        security.set_allowed_directory(str(tmp_path))
        result = get_function(server.read_file_grep)(str(test_file), "xyz")

        assert "Error:" not in result
        assert "No matches found" in result


class TestReadFileRange:
    """Tests for the read_file_range tool."""

    def setup_method(self) -> None:
        """Reset security state before each test."""
        security._allowed_dir = None

    def test_read_valid_range(self, tmp_path: Path) -> None:
        """This function tests reading a valid line range to verify range extraction.

        It requires: a temporary file with multiple lines
        Side effects: creates a temporary file
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        test_file = tmp_path / "test.txt"
        lines = [f"Line {i}" for i in range(1, 11)]
        test_file.write_text("\n".join(lines))

        security.set_allowed_directory(str(tmp_path))
        result = get_function(server.read_file_range)(str(test_file), 3, 7)

        assert "Error:" not in result
        assert "3:Line 3" in result
        assert "4:Line 4" in result
        assert "5:Line 5" in result
        assert "6:Line 6" in result
        assert "7:Line 7" in result

    def test_read_single_range_without_lineno(self, tmp_path: Path) -> None:
        """This function tests reading a single line range without line numbers.

        It requires: a temporary file with multiple lines
        Side effects: creates a temporary file
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        test_file = tmp_path / "test.txt"
        lines = [f"Line {i}" for i in range(1, 11)]
        test_file.write_text("\n".join(lines))

        security.set_allowed_directory(str(tmp_path))
        result = get_function(server.read_file_range)(
            str(test_file), 2, 4, lineno=False
        )

        assert "Error:" not in result
        assert "Line 2" in result
        assert "Line 3" in result
        assert "Line 4" in result

    def test_read_invalid_range(self, tmp_path: Path) -> None:
        """This function tests reading with invalid range to verify error handling.

        It requires: a temporary file
        Side effects: creates a temporary file
        Commonly used by: pytest test runner
        Typical usage: automatically run during test suite
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("Some content")

        security.set_allowed_directory(str(tmp_path))

        # This handles invalid start line which occurs when line number is < 1
        result = get_function(server.read_file_range)(str(test_file), 0, 5)
        assert "Error:" in result
        assert "must be >= 1" in result

        # This handles invalid range which occurs when end < start
        result = get_function(server.read_file_range)(str(test_file), 5, 3)
        assert "Error:" in result
        assert "must be >= start line" in result


def test_simple_stub() -> None:
    """This function provides a simple test stub to verify pytest is working.

    It requires: nothing special
    Side effects: none
    Commonly used by: pytest test runner
    Typical usage: automatically run during test suite
    """
    # This section performs a basic assertion because we need a passing test
    assert True
    assert 1 + 1 == 2

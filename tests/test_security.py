"""Tests for the security module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mcp_file_lens import security


class TestSecurityRestrictions:
    """Tests for file access security restrictions."""

    def setup_method(self) -> None:
        """Reset security state before each test."""
        # Reset the global allowed directory
        security._allowed_dir = None
        security._gitignore_enabled = True

    def test_no_restrictions_by_default(self, tmp_path: Path) -> None:
        """Test that paths are allowed when no restrictions are set."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        assert security.is_path_allowed(str(test_file)) is True

        is_valid, error = security.validate_path(str(test_file))
        assert is_valid is True
        assert error == ""

    def test_set_allowed_directory(self, tmp_path: Path) -> None:
        """Test setting an allowed directory."""
        security.set_allowed_directory(str(tmp_path))

        assert security._allowed_dir == tmp_path.resolve()

    def test_allowed_path_within_directory(self, tmp_path: Path) -> None:
        """Test that paths within allowed directory are permitted."""
        security.set_allowed_directory(str(tmp_path))

        # File directly in allowed dir
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        assert security.is_path_allowed(str(test_file)) is True

        # File in subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        nested_file = subdir / "nested.txt"
        nested_file.write_text("content")
        assert security.is_path_allowed(str(nested_file)) is True

    def test_blocked_path_outside_directory(self, tmp_path: Path) -> None:
        """Test that paths outside allowed directory are blocked."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        security.set_allowed_directory(str(allowed_dir))

        # File outside allowed directory
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("content")

        assert security.is_path_allowed(str(outside_file)) is False

        is_valid, error = security.validate_path(str(outside_file))
        assert is_valid is False
        assert "outside allowed directory" in error

    def test_blocked_parent_directory_traversal(self, tmp_path: Path) -> None:
        """Test that parent directory traversal is blocked."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        security.set_allowed_directory(str(allowed_dir))

        # Try to access parent directory
        assert security.is_path_allowed("../") is False
        assert security.is_path_allowed(str(allowed_dir / ".." / "file.txt")) is False

    def test_nonexistent_allowed_directory(self) -> None:
        """Test that setting a nonexistent allowed directory raises error."""
        with pytest.raises(ValueError, match="does not exist"):
            security.set_allowed_directory("/nonexistent/path")

    def test_file_as_allowed_directory(self, tmp_path: Path) -> None:
        """Test that setting a file as allowed directory raises error."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        with pytest.raises(ValueError, match="not a directory"):
            security.set_allowed_directory(str(test_file))


class TestAuditHook:
    """Tests for the audit hook functionality."""

    def setup_method(self) -> None:
        """Reset security state before each test."""
        security._allowed_dir = None
        security._gitignore_enabled = True

    def test_audit_hook_not_installed_without_allowed_dir(self) -> None:
        """Test that audit hook is not installed when no allowed directory is set."""
        # This should not raise any errors
        security.install_audit_hook()

        # We can't easily test that the hook wasn't installed,
        # but we can verify it doesn't break anything
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"test")
            tf.flush()
            # This should work fine
            with open(tf.name, 'r') as f:
                assert f.read() == "test"

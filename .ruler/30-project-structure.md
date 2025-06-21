# Project structure

## Layout
```
mcp-file-lens/
   src/mcp_file_lens/       # Source package
      __init__.py          # Version export only
      __main__.py          # CLI entry, arg parsing, security setup
      server.py            # MCP tools: list_dir, read_file, read_file_grep, read_files_grep, read_file_range
      security.py          # Path validation, audit hooks, _allowed_dir enforcement
   tests/                   # Mirrors src structure
      test_server.py       # Tool functionality tests
      test_security.py     # Security restriction tests
   pyproject.toml           # Modern Python packaging, dependencies, tool configs
   README.md                # User documentation
   .ruler/                  # Project configs
       mcp.json            # MCP server registration
```

## Key rules
- ALL file operations MUST use security.fs (SecureFileSystem adapter)
- security._allowed_dir restricts access - set via --allowed-dir CLI arg
- SecureFileSystem validates every path before filesystem access
- Use typing imports (List, Dict) not PEP 585 style for pydantic compatibility
- Tests use get_function() helper to unwrap FastMCP decorators
- All tools return plain text (not JSON) for better LLM parsing
- Line numbers in output use "N:content" format (grep -n style)
- Filenames in grep output are relative to current working directory

## Tool signatures
- list_dir(path: str = ".", recursive: bool = False) -> str
- read_file(path: str, lineno: bool = True) -> str
- read_file_grep(path: str, search_string: str, before: int = 0, after: int = 0, context: Optional[int] = None, lineno: bool = True) -> str
- read_files_grep(path: str = ".", search_string: str = "", before: int = 0, after: int = 0, context: Optional[int] = None, lineno: bool = True, filename: bool = True) -> str
- read_file_range(path: str, ranges: list, lineno: bool = True) -> str

## Output formats
- list_dir: Plain text ls -la style with size and filename
- read_file: Plain text with optional line numbers (cat -n style)
- read_file_grep: Plain text grep -n style output with context separators (--)
- read_files_grep: Plain text grep -r style with filename:line:content format
- read_file_range: Plain text with line numbers for specified ranges
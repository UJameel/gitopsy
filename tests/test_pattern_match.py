"""Tests for the pattern matching utilities."""

from __future__ import annotations

import pytest

from gitopsy.scanners.pattern_match import (
    find_python_imports,
    find_javascript_imports,
    detect_secret_patterns,
    find_todo_comments,
)


class TestFindPythonImports:
    def test_finds_python_imports(self) -> None:
        """Finds standard Python import statements."""
        code = """
import os
import sys
from pathlib import Path
from typing import Optional
"""
        imports = find_python_imports(code)
        assert "os" in imports
        assert "sys" in imports
        assert "pathlib" in imports
        assert "typing" in imports

    def test_finds_from_imports(self) -> None:
        """Finds 'from X import Y' style imports."""
        code = "from mymodule import helper\nfrom .relative import thing\n"
        imports = find_python_imports(code)
        assert "mymodule" in imports

    def test_empty_code_returns_empty_list(self) -> None:
        """Empty code returns empty list."""
        assert find_python_imports("") == []


class TestFindJavaScriptImports:
    def test_finds_javascript_imports(self) -> None:
        """Finds ES6 import statements."""
        code = """
import React from 'react';
import { useState } from 'react';
import axios from 'axios';
"""
        imports = find_javascript_imports(code)
        assert "react" in imports
        assert "axios" in imports

    def test_finds_require_calls(self) -> None:
        """Finds CommonJS require() calls."""
        code = "const fs = require('fs');\nconst path = require('path');\n"
        imports = find_javascript_imports(code)
        assert "fs" in imports
        assert "path" in imports

    def test_empty_code_returns_empty_list(self) -> None:
        """Empty code returns empty list."""
        assert find_javascript_imports("") == []


class TestDetectSecretPatterns:
    def test_detects_secret_patterns(self) -> None:
        """Detects common hardcoded secret patterns."""
        code = 'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"\n'
        findings = detect_secret_patterns(code)
        assert len(findings) > 0

    def test_detects_api_key_patterns(self) -> None:
        """Detects generic API key assignments."""
        code = 'api_key = "sk-1234567890abcdef"\n'
        findings = detect_secret_patterns(code)
        assert len(findings) > 0

    def test_clean_code_returns_empty(self) -> None:
        """Clean code with no secrets returns empty list."""
        code = 'DATABASE_URL = os.environ.get("DATABASE_URL")\n'
        findings = detect_secret_patterns(code)
        assert findings == []


class TestFindTodoComments:
    def test_finds_todo_comments(self) -> None:
        """Finds TODO comments in source code."""
        code = "# TODO: fix this\nx = 1\n# FIXME: broken\n"
        todos = find_todo_comments(code)
        assert len(todos) >= 2

    def test_finds_hack_comments(self) -> None:
        """Finds HACK comments."""
        code = "# HACK: temporary workaround\n"
        todos = find_todo_comments(code)
        assert len(todos) >= 1

    def test_clean_code_returns_empty(self) -> None:
        """Code with no TODO-style comments returns empty."""
        code = "x = 1\n# This is a normal comment\n"
        todos = find_todo_comments(code)
        assert todos == []

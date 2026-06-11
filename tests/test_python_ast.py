"""Tests for Python AST engine rules."""

import ast
from pathlib import Path

from unified_lint.engines.python_ast import (
    check_api_result_wrapper,
    check_no_bare_except,
    check_no_hardcoded_secret,
    check_no_n_plus_one,
    check_service_ctx_first,
)


def test_service_ctx_first_detects_violation():
    """Service methods without ctx should be flagged."""
    code = """
class UserService:
    def get_user(self, user_id: int):
        pass
"""
    tree = ast.parse(code)
    violations = check_service_ctx_first(Path("service/user.py"), tree)
    assert len(violations) == 1
    assert "ctx" in violations[0].message
    assert "get_user" in violations[0].message


def test_service_ctx_first_passes_with_ctx():
    """Service methods with ctx should not be flagged."""
    code = """
class UserService:
    def get_user(self, ctx, user_id: int):
        pass
"""
    tree = ast.parse(code)
    violations = check_service_ctx_first(Path("service/user.py"), tree)
    assert len(violations) == 0


def test_api_result_wrapper_detects_violation():
    """API functions returning raw dicts should be flagged."""
    code = """
def get_users():
    return {"users": []}
"""
    tree = ast.parse(code)
    violations = check_api_result_wrapper(Path("api/users.py"), tree)
    assert len(violations) == 1
    assert "raw dict" in violations[0].message


def test_api_result_wrapper_passes_with_wrapper():
    """API functions returning Result should not be flagged."""
    code = """
def get_users():
    return Result(data={"users": []})
"""
    tree = ast.parse(code)
    violations = check_api_result_wrapper(Path("api/users.py"), tree)
    assert len(violations) == 0


def test_api_result_wrapper_ignores_non_api():
    """Non-api files should not be checked."""
    code = """
def get_users():
    return {"users": []}
"""
    tree = ast.parse(code)
    violations = check_api_result_wrapper(Path("service/users.py"), tree)
    assert len(violations) == 0


def test_no_bare_except_detects_violation():
    """Bare except should be flagged."""
    code = """
try:
    do_something()
except:
    pass
"""
    tree = ast.parse(code)
    violations = check_no_bare_except(Path("main.py"), tree)
    assert len(violations) == 1
    assert "Bare except" in violations[0].message


def test_no_bare_except_passes_with_type():
    """Except with specific type should not be flagged."""
    code = """
try:
    do_something()
except ValueError:
    pass
"""
    tree = ast.parse(code)
    violations = check_no_bare_except(Path("main.py"), tree)
    assert len(violations) == 0


def test_no_hardcoded_secret_detects_password():
    """Hardcoded password should be flagged."""
    code = """
password = "secret123"
"""
    tree = ast.parse(code)
    violations = check_no_hardcoded_secret(Path("config.py"), tree)
    assert len(violations) == 1
    assert "password" in violations[0].message


def test_no_hardcoded_secret_passes_with_env():
    """Password from environment should not be flagged."""
    code = """
import os
password = os.getenv("PASSWORD")
"""
    tree = ast.parse(code)
    violations = check_no_hardcoded_secret(Path("config.py"), tree)
    assert len(violations) == 0


def test_no_n_plus_one_detects_query_in_loop():
    """Database query in loop should be flagged."""
    code = """
for user_id in user_ids:
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
"""
    tree = ast.parse(code)
    violations = check_no_n_plus_one(Path("repo.py"), tree)
    assert len(violations) == 1
    assert "N+1" in violations[0].message


def test_no_n_plus_one_passes_without_loop():
    """Database query outside loop should not be flagged."""
    code = """
cursor.execute("SELECT * FROM users")
"""
    tree = ast.parse(code)
    violations = check_no_n_plus_one(Path("repo.py"), tree)
    assert len(violations) == 0

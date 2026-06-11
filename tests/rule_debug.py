"""Test file with intentional violations for rule debugging."""


class TestService:
    """Service with ctx violations."""

    def method_without_ctx(self, user_id: int) -> bool:
        """VIOLATION: missing ctx parameter."""
        return True

    def method_with_ctx(self, ctx, user_id: int) -> bool:
        """CORRECT: has ctx."""
        return True

    def another_violation(self, name: str, age: int):
        """VIOLATION: missing ctx parameter."""
        pass


def api_returns_raw_dict():
    """VIOLATION: returns raw dict."""
    return {"status": "ok", "data": [1, 2, 3]}


def api_returns_result():
    """CORRECT: returns Result."""
    return Result(data=[1, 2, 3])


def loop_with_query():
    """VIOLATION: N+1 query pattern."""
    users = get_users()
    for user in users:
        cursor.execute("SELECT * FROM orders WHERE user_id = %s", (user.id,))


class Result:
    """Result wrapper."""

    def __init__(self, data=None):
        self.data = data

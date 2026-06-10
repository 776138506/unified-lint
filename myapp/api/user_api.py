"""User API - 用户接口"""

from typing import Any, Dict


class Result:
    """统一返回封装"""

    def __init__(self, data: Any = None, error: str = ""):
        self.data = data
        self.error = error


def get_user_api(user_id: int) -> Dict:
    """违规：返回裸 dict，没有用 Result 封装"""
    return {"id": user_id, "name": "test"}

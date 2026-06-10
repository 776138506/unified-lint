"""User service - 用户业务服务"""

from typing import Optional, Any
from domain.models import User

# ctx 类型别名
Context = Any


class UserService:
    def get_user(self, user_id: int) -> Optional[User]:
        """获取用户 - 违规：缺少 ctx 参数"""
        pass

    def create_user(self, ctx: Context, name: str, email: str) -> User:
        """创建用户 - 正确：有 ctx 参数"""
        pass

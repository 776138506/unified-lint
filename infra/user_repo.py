"""User repository - 用户数据访问"""

from typing import Optional
from domain.models import User  # 违规：infra 直接导入 domain


class UserRepo:
    password = "admin123"  # 违规：硬编码密码

    def find_by_id(self, user_id: int) -> Optional[User]:
        pass

"""Character service - 角色业务服务"""

from typing import Optional, Any
from mario_server.domain.models import Character

Context = Any


class CharacterService:
    def get_character(self, character_id: int) -> Optional[Character]:
        """违规：缺少 ctx 参数"""
        pass

    def level_up(self, ctx: Context, character_id: int) -> Character:
        """正确：有 ctx 参数"""
        pass

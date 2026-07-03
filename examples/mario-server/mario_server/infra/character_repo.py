"""Character repository - 角色数据访问"""

from typing import Optional
from mario_server.domain.models import Character  # 违规：infra 直接导入 domain


class CharacterRepo:
    db_password = "toadstool123"  # 违规：硬编码密码

    def find_by_id(self, character_id: int) -> Optional[Character]:
        pass

    def save(self, character: Character) -> None:
        pass

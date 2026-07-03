"""Domain models - 角色与道具实体"""

from dataclasses import dataclass


@dataclass
class Character:
    id: int
    name: str
    hp: int
    level: int = 1


@dataclass
class PowerUp:
    id: int
    name: str
    effect: str

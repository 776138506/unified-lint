"""Domain models - 核心业务实体"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: int
    name: str
    email: str


@dataclass
class Order:
    id: int
    user_id: int
    total: float
    status: str = "pending"

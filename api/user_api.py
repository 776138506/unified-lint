"""User API - 用户接口"""

from service.user_service import UserService


def get_user_api(user_id: int):
    """获取用户 API - 违规：返回裸对象，没有封装 Result"""
    service = UserService()
    return service.get_user(user_id)

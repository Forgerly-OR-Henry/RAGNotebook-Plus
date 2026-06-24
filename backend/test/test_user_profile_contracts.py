"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from sqlalchemy import String

from mvc.models.user_model import User
from mvc.schemas import UserResponse, UserUpdateRequest


def test_user_gender_profile_contract_accepts_text_values():
    """
    用途：执行test user gender profile contract accepts text values相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    assert isinstance(User.__table__.c.gender.type, String)

    update = UserUpdateRequest(gender="nonbinary")
    response = UserResponse(username="user", email="user@example.com", gender=update.gender)

    assert response.gender == "nonbinary"

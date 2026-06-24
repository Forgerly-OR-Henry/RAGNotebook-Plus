"""
模块职责：Pydantic schema 模块，负责声明接口请求、响应和嵌套数据结构。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - username（str | None）：保存username相关状态、配置或数据字段。
    - email（str | None）：保存email相关状态、配置或数据字段。
    - password（str）：保存password相关状态、配置或数据字段。
    """
    username: str | None = None
    email: str | None = None
    password: str = Field(..., min_length=6, max_length=20)


class RegisterRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - username（str）：保存username相关状态、配置或数据字段。
    - email（EmailStr）：保存email相关状态、配置或数据字段。
    - password（str）：保存password相关状态、配置或数据字段。
    - confirm_password（str）：保存confirm_password相关状态、配置或数据字段。
    - telephone（str | None）：保存telephone相关状态、配置或数据字段。
    """
    username: str
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=20)
    confirm_password: str = Field(..., min_length=6, max_length=20)
    telephone: str | None = None


class ResetPasswordRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - old_password（str）：保存old_password相关状态、配置或数据字段。
    - new_password（str）：保存new_password相关状态、配置或数据字段。
    - confirm_password（str）：保存confirm_password相关状态、配置或数据字段。
    """
    old_password: str = Field(..., min_length=6, max_length=20)
    new_password: str = Field(..., min_length=6, max_length=20)
    confirm_password: str = Field(..., min_length=6, max_length=20)


class UserUpdateRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - username（str | None）：保存username相关状态、配置或数据字段。
    - email（EmailStr | None）：保存email相关状态、配置或数据字段。
    - telephone（str | None）：保存telephone相关状态、配置或数据字段。
    - avatar（str | None）：保存avatar相关状态、配置或数据字段。
    - gender（str | None）：保存gender相关状态、配置或数据字段。
    - bio（str | None）：保存bio相关状态、配置或数据字段。
    """
    username: str | None = None
    email: EmailStr | None = None
    telephone: str | None = None
    avatar: str | None = None
    gender: str | None = Field(default=None, max_length=50)
    bio: str | None = None


class TokenRefreshRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - token（str）：保存token相关状态、配置或数据字段。
    """
    token: str


class UserResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - uuid（str | None）：保存uuid相关状态、配置或数据字段。
    - user_id（str | None）：保存user_id相关状态、配置或数据字段。
    - id（str | None）：保存id相关状态、配置或数据字段。
    - username（str）：保存username相关状态、配置或数据字段。
    - email（str）：保存email相关状态、配置或数据字段。
    - telephone（str | None）：保存telephone相关状态、配置或数据字段。
    - gender（str | None）：保存gender相关状态、配置或数据字段。
    - bio（str | None）：保存bio相关状态、配置或数据字段。
    - avatar（str | None）：保存avatar相关状态、配置或数据字段。
    - status（int | None）：保存status相关状态、配置或数据字段。
    - date_joined（datetime | None）：保存date_joined相关状态、配置或数据字段。
    - last_login（datetime | None）：保存last_login相关状态、配置或数据字段。
    - is_active（bool | None）：保存is_active相关状态、配置或数据字段。
    """
    uuid: str | None = None
    user_id: str | None = None
    id: str | None = None
    username: str
    email: str
    telephone: str | None = None
    gender: str | None = None
    bio: str | None = None
    avatar: str | None = None
    status: int | None = None
    date_joined: datetime | None = None
    last_login: datetime | None = None
    is_active: bool | None = None


class LoginResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - message（str）：保存message相关状态、配置或数据字段。
    - user（UserResponse）：保存user相关状态、配置或数据字段。
    - token（str）：保存token相关状态、配置或数据字段。
    """
    message: str
    user: UserResponse
    token: str


class RegisterResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - status（int）：保存status相关状态、配置或数据字段。
    - message（str）：保存message相关状态、配置或数据字段。
    - user（UserResponse）：保存user相关状态、配置或数据字段。
    - token（str）：保存token相关状态、配置或数据字段。
    """
    status: int
    message: str
    user: UserResponse
    token: str


class ActionResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - message（str）：保存message相关状态、配置或数据字段。
    - user（UserResponse | None）：保存user相关状态、配置或数据字段。
    - token（str | None）：保存token相关状态、配置或数据字段。
    """
    message: str
    user: UserResponse | None = None
    token: str | None = None


class UserDetailResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - success（bool）：保存success相关状态、配置或数据字段。
    - message（str）：保存message相关状态、配置或数据字段。
    - data（UserResponse）：保存data相关状态、配置或数据字段。
    """
    success: bool
    message: str
    data: UserResponse

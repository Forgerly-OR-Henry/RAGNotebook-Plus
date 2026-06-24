"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from mvc.models.user_model import User, UserStatusChoice
from mvc.repositories.runtime_store import delete_cache
from mvc.repositories.user_repository import UserRepository, user_repository
from mvc.schemas import LoginRequest, RegisterRequest, ResetPasswordRequest, TokenRefreshRequest, UserResponse, UserUpdateRequest
from utils.auth_utils import blacklist_token, decode_django_jwt, generate_token, get_user_info_cached, hash_password, verify_password


class UserService:
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：
    - repository（实例属性，由构造函数注入或初始化）：保存repository相关状态、配置或数据字段。
    """
    def __init__(self, repository: UserRepository | None = None):
        """
        用途：执行init相关业务逻辑。

        参数：
        - repository（UserRepository | None）：调用方传入的repository数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.repository = repository or user_repository

    @staticmethod
    def user_to_response(user: User) -> UserResponse:
        """
        用途：执行user to response相关业务逻辑。

        参数：
        - user（User）：调用方传入的user数据或控制参数，用于驱动本函数处理流程。

        返回：UserResponse；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return UserResponse(
            uuid=user.uuid,
            user_id=user.uuid,
            id=user.uuid,
            username=user.username,
            email=user.email,
            telephone=user.telephone,
            gender=user.gender,
            bio=user.bio,
            avatar=user.avatar,
            status=user.status,
            date_joined=user.date_joined,
            last_login=user.last_login,
            is_active=user.is_active,
        )

    async def login(self, req: LoginRequest) -> dict:
        """
        用途：异步执行login相关业务流程。

        参数：
        - req（LoginRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        user = await self.repository.get_by_username_or_email(req.username, req.email)
        if not user:
            raise HTTPException(status_code=400, detail="用户名或邮箱不存在")
        if not verify_password(req.password, user.password):
            raise HTTPException(status_code=400, detail="密码错误")
        if user.status != UserStatusChoice.ACTIVE:
            raise HTTPException(status_code=400, detail="用户状态异常，请检查是否激活或已被锁定")

        user = await self.repository.touch_last_login(user.uuid) or user
        token, _ = generate_token(user.uuid, user.username, user.email)
        return {
            "message": f"{user.username} 登录成功",
            "user": self.user_to_response(user).model_dump(),
            "token": token,
        }

    async def register(self, req: RegisterRequest) -> dict:
        """
        用途：异步执行register相关业务流程。

        参数：
        - req（RegisterRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if req.password != req.confirm_password:
            raise HTTPException(status_code=400, detail={"confirm_password": "密码和确认密码不一致"})
        if await self.repository.email_exists(req.email):
            raise HTTPException(status_code=400, detail={"email": "该邮箱已被注册"})
        if req.telephone and await self.repository.telephone_exists(req.telephone):
            raise HTTPException(status_code=400, detail={"telephone": "该电话号码已被注册"})

        user = await self.repository.create_user(
            username=req.username,
            email=req.email,
            telephone=req.telephone,
            password_hash=hash_password(req.password),
        )
        token, _ = generate_token(user.uuid, user.username, user.email)
        return {
            "status": 201,
            "message": f"{user.username} 注册成功",
            "user": self.user_to_response(user).model_dump(),
            "token": token,
        }

    async def reset_password(self, req: ResetPasswordRequest, user_id: str, token: str) -> dict:
        """
        用途：重置reset password相关的数据或流程。

        参数：
        - req（ResetPasswordRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - token（str）：调用方传入的token数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if req.new_password != req.confirm_password:
            raise HTTPException(status_code=400, detail="新密码和确认密码不一致")
        if req.new_password == req.old_password:
            raise HTTPException(status_code=400, detail="新密码不能和旧密码相同")

        user = await self.repository.get_by_uuid(user_id)
        if not user:
            raise HTTPException(status_code=400, detail="用户不存在")
        if not verify_password(req.old_password, user.password):
            raise HTTPException(status_code=400, detail="请检查旧密码是否正确")

        await blacklist_token(token)
        user = await self.repository.update_password(user_id, hash_password(req.new_password)) or user
        await delete_cache(f"user:{user_id}")
        new_token, _ = generate_token(user.uuid, user.username, user.email)
        return {"message": "密码重置成功", "token": new_token}

    async def refresh_token(self, req: TokenRefreshRequest) -> dict:
        """
        用途：异步执行refresh token相关业务流程。

        参数：
        - req（TokenRefreshRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        payload = decode_django_jwt(req.token)
        if not payload:
            raise HTTPException(status_code=401, detail="Token无效")

        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token中未包含用户信息")

        user = await self.repository.get_by_uuid(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        if user.status != UserStatusChoice.ACTIVE:
            raise HTTPException(status_code=401, detail="用户状态异常")

        await blacklist_token(req.token)
        new_token, expire_time = generate_token(user.uuid, user.username, user.email)
        return {"message": "Token刷新成功", "token": new_token, "expire_time": expire_time}

    async def get_detail(self, user_id: str, credentials: HTTPAuthorizationCredentials) -> dict:
        """
        用途：读取或查询get detail相关的数据或流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - credentials（HTTPAuthorizationCredentials）：调用方传入的credentials数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        user_info = await get_user_info_cached(user_id, credentials)
        return {
            "success": True,
            "message": "获取用户详情成功",
            "data": user_info,
        }

    async def update_user(self, req: UserUpdateRequest, user_id: str, token: str) -> dict:
        """
        用途：更新update user相关的数据或流程。

        参数：
        - req（UserUpdateRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - token（str）：调用方传入的token数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        existing = await self.repository.get_by_uuid(user_id)
        if not existing:
            raise HTTPException(status_code=400, detail="用户不存在")
        update_data = req.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"]:
            email = str(update_data["email"]).strip()
            if await self.repository.email_exists(email, exclude_user_id=user_id):
                raise HTTPException(status_code=400, detail={"email": "该邮箱已被注册"})
            update_data["email"] = email

        if "telephone" in update_data and update_data["telephone"]:
            update_data["telephone"] = str(update_data["telephone"]).strip()
        telephone = update_data.get("telephone")
        if telephone and await self.repository.telephone_exists(str(telephone), exclude_user_id=user_id):
            raise HTTPException(status_code=400, detail={"telephone": "该电话号码已被注册"})

        if "gender" in update_data:
            gender = str(update_data["gender"] or "").strip()
            update_data["gender"] = gender or None

        user = await self.repository.update_user(user_id, update_data) or existing
        await blacklist_token(token)
        await delete_cache(f"user:{user_id}")
        new_token, _ = generate_token(user.uuid, user.username, user.email)
        return {
            "message": "用户信息更新成功",
            "user": self.user_to_response(user).model_dump(),
            "token": new_token,
        }

    async def logout(self, token: str) -> dict:
        """
        用途：异步执行logout相关业务流程。

        参数：
        - token（str）：调用方传入的token数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        await blacklist_token(token)
        return {"message": "用户注销成功"}


_user_service = UserService()


def get_user_service() -> UserService:
    """
    用途：读取或查询get user service相关的数据或流程。

    参数：无显式业务参数。

    返回：UserService；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return _user_service

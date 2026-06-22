from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from models.user_model import User, UserStatusChoice
from repositories.runtime_store import delete_cache
from repositories.user_repository import UserRepository, user_repository
from schemas import LoginRequest, RegisterRequest, ResetPasswordRequest, TokenRefreshRequest, UserResponse, UserUpdateRequest
from utils.auth_utils import blacklist_token, decode_django_jwt, generate_token, get_user_info_cached, hash_password, verify_password


class UserService:
    def __init__(self, repository: UserRepository | None = None):
        self.repository = repository or user_repository

    @staticmethod
    def user_to_response(user: User) -> UserResponse:
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
        user_info = await get_user_info_cached(user_id, credentials)
        return {
            "success": True,
            "message": "获取用户详情成功",
            "data": user_info,
        }

    async def update_user(self, req: UserUpdateRequest, user_id: str, token: str) -> dict:
        existing = await self.repository.get_by_uuid(user_id)
        if not existing:
            raise HTTPException(status_code=400, detail="用户不存在")
        if req.telephone and await self.repository.telephone_exists(req.telephone, exclude_user_id=user_id):
            raise HTTPException(status_code=400, detail={"telephone": "该电话号码已被注册"})

        user = await self.repository.update_user(user_id, req.model_dump(exclude_unset=True)) or existing
        await blacklist_token(token)
        await delete_cache(f"user:{user_id}")
        new_token, _ = generate_token(user.uuid, user.username, user.email)
        return {
            "message": "用户信息更新成功",
            "user": self.user_to_response(user).model_dump(),
            "token": new_token,
        }

    async def logout(self, token: str) -> dict:
        await blacklist_token(token)
        return {"message": "用户注销成功"}


_user_service = UserService()


def get_user_service() -> UserService:
    return _user_service

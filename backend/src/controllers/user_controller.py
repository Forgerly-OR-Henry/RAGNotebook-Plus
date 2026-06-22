from fastapi import APIRouter, Depends, UploadFile
from fastapi.security import HTTPAuthorizationCredentials

from schemas import LoginRequest, RegisterRequest, ResetPasswordRequest, TokenRefreshRequest, UserUpdateRequest
from services.file_service import FileService, get_file_service
from services.user_service import UserService, get_user_service
from utils.auth_utils import get_current_user_id, security

user_router = APIRouter(tags=["user"], prefix="/user")
file_router = APIRouter(tags=["file"], prefix="/file")


@user_router.post("/login/")
async def login(req: LoginRequest, service: UserService = Depends(get_user_service)):
    return await service.login(req)


@user_router.post("/register/")
async def register(req: RegisterRequest, service: UserService = Depends(get_user_service)):
    return await service.register(req)


@user_router.post("/reset-password/")
async def reset_password(
    req: ResetPasswordRequest,
    user_id: str = Depends(get_current_user_id),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: UserService = Depends(get_user_service),
):
    return await service.reset_password(req, user_id, credentials.credentials)


@user_router.post("/refresh-token/")
async def refresh_token(req: TokenRefreshRequest, service: UserService = Depends(get_user_service)):
    return await service.refresh_token(req)


@user_router.get("/detail/")
async def get_user_info(
    user_id: str = Depends(get_current_user_id),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: UserService = Depends(get_user_service),
):
    return await service.get_detail(user_id, credentials)


@user_router.put("/update/")
async def update_user(
    req: UserUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: UserService = Depends(get_user_service),
):
    return await service.update_user(req, user_id, credentials.credentials)


@user_router.post("/logout/")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: UserService = Depends(get_user_service),
):
    return await service.logout(credentials.credentials)


@file_router.post("/upload/")
async def upload_file(
    file: UploadFile,
    user_id: str = Depends(get_current_user_id),
    service: FileService = Depends(get_file_service),
):
    return await service.upload_avatar(file, user_id)

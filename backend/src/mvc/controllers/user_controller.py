"""
模块职责：FastAPI 路由控制器模块，负责请求参数绑定、权限依赖和服务层调用。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.security import HTTPAuthorizationCredentials

from mvc.schemas import LoginRequest, RegisterRequest, ResetPasswordRequest, TokenRefreshRequest, UserUpdateRequest
from mvc.services.file_service import FileService, get_file_service
from mvc.services.user_service import UserService, get_user_service
from utils.auth_utils import get_current_user_id, security

user_router = APIRouter(tags=["user"], prefix="/user")
file_router = APIRouter(tags=["file"], prefix="/file")


@user_router.post("/login/")
async def login(req: LoginRequest, service: UserService = Depends(get_user_service)):
    """
    用途：异步执行login相关业务流程。

    参数：
    - req（LoginRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。
    - service（UserService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await service.login(req)


@user_router.post("/register/")
async def register(req: RegisterRequest, service: UserService = Depends(get_user_service)):
    """
    用途：异步执行register相关业务流程。

    参数：
    - req（RegisterRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。
    - service（UserService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await service.register(req)


@user_router.post("/reset-password/")
async def reset_password(
    req: ResetPasswordRequest,
    user_id: str = Depends(get_current_user_id),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: UserService = Depends(get_user_service),
):
    """
    用途：重置reset password相关的数据或流程。

    参数：
    - req（ResetPasswordRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - credentials（HTTPAuthorizationCredentials）：调用方传入的credentials数据或控制参数，用于驱动本函数处理流程。
    - service（UserService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await service.reset_password(req, user_id, credentials.credentials)


@user_router.post("/refresh-token/")
async def refresh_token(req: TokenRefreshRequest, service: UserService = Depends(get_user_service)):
    """
    用途：异步执行refresh token相关业务流程。

    参数：
    - req（TokenRefreshRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。
    - service（UserService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await service.refresh_token(req)


@user_router.get("/detail/")
async def get_user_info(
    user_id: str = Depends(get_current_user_id),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: UserService = Depends(get_user_service),
):
    """
    用途：读取或查询get user info相关的数据或流程。

    参数：
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - credentials（HTTPAuthorizationCredentials）：调用方传入的credentials数据或控制参数，用于驱动本函数处理流程。
    - service（UserService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await service.get_detail(user_id, credentials)


@user_router.put("/update/")
async def update_user(
    req: UserUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: UserService = Depends(get_user_service),
):
    """
    用途：更新update user相关的数据或流程。

    参数：
    - req（UserUpdateRequest）：调用方传入的req数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - credentials（HTTPAuthorizationCredentials）：调用方传入的credentials数据或控制参数，用于驱动本函数处理流程。
    - service（UserService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await service.update_user(req, user_id, credentials.credentials)


@user_router.post("/logout/")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: UserService = Depends(get_user_service),
):
    """
    用途：异步执行logout相关业务流程。

    参数：
    - credentials（HTTPAuthorizationCredentials）：调用方传入的credentials数据或控制参数，用于驱动本函数处理流程。
    - service（UserService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await service.logout(credentials.credentials)


@file_router.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    service: FileService = Depends(get_file_service),
):
    """
    用途：上传upload file相关的数据或流程。

    参数：
    - file（UploadFile）：调用方传入的file数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - service（FileService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await service.upload_avatar(file, user_id)


@file_router.get("/avatar/{object_id}")
async def get_avatar_file(
    object_id: str,
    service: FileService = Depends(get_file_service),
):
    """
    用途：读取或查询get avatar file相关的数据或流程。

    参数：
    - object_id（str）：调用方传入的object_id数据或控制参数，用于驱动本函数处理流程。
    - service（FileService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await service.get_avatar_response(object_id)

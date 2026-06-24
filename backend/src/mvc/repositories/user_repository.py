"""
模块职责：仓储模块，负责封装持久化或运行时状态读写逻辑。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from datetime import datetime

from sqlalchemy import select

from db.db_config import AsyncSessionLocal
from mvc.models.user_model import User, UserStatusChoice


class UserRepository:
    """
    用途：仓储类，用于封装数据库或索引存取细节。

    属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
    """
    async def get_by_username_or_email(self, username: str | None, email: str | None) -> User | None:
        """
        用途：读取或查询get by username or email相关的数据或流程。

        参数：
        - username（str | None）：调用方传入的username数据或控制参数，用于驱动本函数处理流程。
        - email（str | None）：调用方传入的email数据或控制参数，用于驱动本函数处理流程。

        返回：User | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where((User.username == username) | (User.email == email)))
            return result.scalar_one_or_none()

    async def get_by_uuid(self, user_id: str) -> User | None:
        """
        用途：读取或查询get by uuid相关的数据或流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：User | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.uuid == user_id))
            return result.scalar_one_or_none()

    async def email_exists(self, email: str, exclude_user_id: str | None = None) -> bool:
        """
        用途：异步执行email exists相关业务流程。

        参数：
        - email（str）：调用方传入的email数据或控制参数，用于驱动本函数处理流程。
        - exclude_user_id（str | None）：调用方传入的exclude_user_id数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.email == email)
            if exclude_user_id:
                stmt = stmt.where(User.uuid != exclude_user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def telephone_exists(self, telephone: str, exclude_user_id: str | None = None) -> bool:
        """
        用途：异步执行telephone exists相关业务流程。

        参数：
        - telephone（str）：调用方传入的telephone数据或控制参数，用于驱动本函数处理流程。
        - exclude_user_id（str | None）：调用方传入的exclude_user_id数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telephone == telephone)
            if exclude_user_id:
                stmt = stmt.where(User.uuid != exclude_user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def create_user(self, *, username: str, email: str, telephone: str | None, password_hash: str) -> User:
        """
        用途：创建create user相关的数据或流程。

        参数：
        - username（str）：调用方传入的username数据或控制参数，用于驱动本函数处理流程。
        - email（str）：调用方传入的email数据或控制参数，用于驱动本函数处理流程。
        - telephone（str | None）：调用方传入的telephone数据或控制参数，用于驱动本函数处理流程。
        - password_hash（str）：调用方传入的password_hash数据或控制参数，用于驱动本函数处理流程。

        返回：User；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            user = User(
                username=username,
                email=email,
                telephone=telephone,
                password=password_hash,
                status=UserStatusChoice.ACTIVE,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def touch_last_login(self, user_id: str) -> User | None:
        """
        用途：异步执行touch last login相关业务流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：User | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.uuid == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return None
            user.last_login = datetime.now()
            await session.commit()
            await session.refresh(user)
            return user

    async def update_password(self, user_id: str, password_hash: str) -> User | None:
        """
        用途：更新update password相关的数据或流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - password_hash（str）：调用方传入的password_hash数据或控制参数，用于驱动本函数处理流程。

        返回：User | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.uuid == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return None
            user.password = password_hash
            await session.commit()
            await session.refresh(user)
            return user

    async def update_user(self, user_id: str, data: dict) -> User | None:
        """
        用途：更新update user相关的数据或流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - data（dict）：调用方传入的data数据或控制参数，用于驱动本函数处理流程。

        返回：User | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.uuid == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return None
            for field, value in data.items():
                setattr(user, field, value)
            await session.commit()
            await session.refresh(user)
            return user

    async def update_avatar(self, user_id: str, avatar_url: str) -> None:
        """
        用途：更新update avatar相关的数据或流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - avatar_url（str）：调用方传入的avatar_url数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.uuid == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            user.avatar = avatar_url
            await session.commit()


user_repository = UserRepository()

from datetime import datetime

from sqlalchemy import select

from db.db_config import AsyncSessionLocal
from models.user_model import User, UserStatusChoice


class UserRepository:
    async def get_by_username_or_email(self, username: str | None, email: str | None) -> User | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where((User.username == username) | (User.email == email)))
            return result.scalar_one_or_none()

    async def get_by_uuid(self, user_id: str) -> User | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.uuid == user_id))
            return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none() is not None

    async def telephone_exists(self, telephone: str, exclude_user_id: str | None = None) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telephone == telephone)
            if exclude_user_id:
                stmt = stmt.where(User.uuid != exclude_user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def create_user(self, *, username: str, email: str, telephone: str | None, password_hash: str) -> User:
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
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.uuid == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            user.avatar = avatar_url
            await session.commit()


user_repository = UserRepository()

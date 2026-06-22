from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import text

from core.logger_handler import logger
from db.db_config import AsyncSessionLocal


class MD5Store:
    """MD5 metadata backed by PostgreSQL."""

    async def check_md5_hex(self, md5_for_check: str, user_id: str = None) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM knowledge_md5_records
            WHERE user_id = :user_id AND md5 = :md5
            LIMIT 1
            """
        )
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(stmt, {"user_id": user_id or "__public__", "md5": md5_for_check})
                return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"【向量数据库】检查MD5时出错: {e}")
            return False

    async def save_md5_hex(self, md5_hex: str, filename: str = None, original_filename: str = None, user_id: str = None):
        stmt = text(
            """
            INSERT INTO knowledge_md5_records (user_id, md5, filename, original_filename, upload_time)
            VALUES (:user_id, :md5, :filename, :original_filename, :upload_time)
            ON CONFLICT (user_id, md5) DO UPDATE SET
                filename = EXCLUDED.filename,
                original_filename = EXCLUDED.original_filename,
                upload_time = EXCLUDED.upload_time
            """
        )
        params = {
            "user_id": user_id or "__public__",
            "md5": md5_hex,
            "filename": filename,
            "original_filename": original_filename,
            "upload_time": datetime.now(timezone.utc),
        }
        async with AsyncSessionLocal() as session:
            await session.execute(stmt, params)
            await session.commit()

    def save_md5_hex_sync(self, md5_hex: str, filename: str = None, original_filename: str = None, user_id: str = None):
        asyncio.run(self.save_md5_hex(md5_hex, filename, original_filename, user_id))

    async def delete_user_md5(self, user_id: str):
        stmt = text("DELETE FROM knowledge_md5_records WHERE user_id = :user_id")
        async with AsyncSessionLocal() as session:
            await session.execute(stmt, {"user_id": user_id or "__public__"})
            await session.commit()
        logger.info(f"【MD5存储】已删除用户 {user_id} 的MD5记录")

    async def delete_by_filename(self, user_id: str, filename: str):
        select_stmt = text(
            """
            SELECT md5
            FROM knowledge_md5_records
            WHERE user_id = :user_id
              AND (filename = :filename OR original_filename = :filename)
            ORDER BY upload_time DESC
            LIMIT 1
            """
        )
        delete_stmt = text(
            """
            DELETE FROM knowledge_md5_records
            WHERE user_id = :user_id
              AND (filename = :filename OR original_filename = :filename)
            """
        )
        params = {"user_id": user_id or "__public__", "filename": filename}
        async with AsyncSessionLocal() as session:
            result = await session.execute(select_stmt, params)
            md5 = result.scalar_one_or_none()
            if md5 is None:
                return None
            await session.execute(delete_stmt, params)
            await session.commit()

        logger.info(f"【MD5存储】已删除用户 {user_id} 的文件 {filename} 的MD5记录")
        return md5

    async def delete_single_md5(self, user_id: str, md5_to_delete: str) -> bool:
        stmt = text(
            """
            DELETE FROM knowledge_md5_records
            WHERE user_id = :user_id AND md5 = :md5
            """
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, {"user_id": user_id or "__public__", "md5": md5_to_delete})
            await session.commit()

        success = (result.rowcount or 0) > 0
        if success:
            logger.info(f"【MD5存储】已删除用户 {user_id} 的MD5记录: {md5_to_delete}")
        return success

    async def get_md5_info(self, user_id: str, md5_value: str):
        stmt = text(
            """
            SELECT md5, filename, original_filename, upload_time
            FROM knowledge_md5_records
            WHERE user_id = :user_id AND md5 = :md5
            LIMIT 1
            """
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, {"user_id": user_id or "__public__", "md5": md5_value})
            row = result.mappings().one_or_none()
        return self._row_to_record(row) if row else None

    async def get_all_md5_records(self, user_id: str) -> list:
        stmt = text(
            """
            SELECT md5, filename, original_filename, upload_time
            FROM knowledge_md5_records
            WHERE user_id = :user_id
            ORDER BY upload_time DESC, filename ASC
            """
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, {"user_id": user_id or "__public__"})
            rows = result.mappings().all()
        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def _row_to_record(row) -> dict:
        upload_time = row["upload_time"]
        return {
            "md5": row["md5"],
            "filename": row["filename"],
            "original_filename": row["original_filename"],
            "upload_time": upload_time.isoformat() if upload_time else None,
        }

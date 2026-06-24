"""
模块职责：仓储模块，负责封装持久化或运行时状态读写逻辑。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from collections.abc import Callable
from functools import wraps
from typing import Generic, TypeVar

from mvc.repositories.runtime_store import delete_cache, delete_cache_pattern, get_cache, set_cache

T = TypeVar("T")


class PostgresCache(Generic[T]):
    """
    PostgreSQL缓存管理类

    提供通用的缓存操作: 自动缓存和过期时间设置
    """

    @staticmethod
    async def get_or_set(
            key: str,
            func: Callable[..., T],
            *args,
            expire: int = 3600,
            **kwargs
    ) -> T:
        """
        获取缓存，如果缓存不存在则执行函数并缓存结果

        :param key: 缓存键
        :param func: 要执行的函数
        :param args: 函数参数
        :param kwargs: 函数关键字参数
        :param expire: 缓存过期时间(秒)
        :return: 函数执行结果
        """
        # 尝试从缓存获取
        # 将缓存键统一标准化为字符串，确保 PostgreSQL 查询条件类型稳定。
        cache_key = str(key)
        cached_data = await get_cache(cache_key)

        if cached_data is not None:
            return cached_data

        print("【PostgresCache】缓存不存在")

        # 缓存不存在，执行函数
        result = await func(*args, **kwargs)

        # 将结果转换为可序列化的格式
        def convert_to_serializable(obj):
            """将对象转换为可序列化的格式"""
            if obj is None:
                return None
            elif isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif hasattr(obj, '__dict__'):
                # 处理模型对象
                obj_dict = {}
                for key, value in obj.__dict__.items():
                    # 排除内部属性和不可序列化的属性
                    if not key.startswith('_') and not hasattr(value, '__dict__'):
                        obj_dict[key] = convert_to_serializable(value)
                return obj_dict
            else:
                # 其他类型尝试转换为字符串
                try:
                    return str(obj)
                except Exception as e:
                    print(f"转换对象为字符串时出错: {e}")
                    return None

        # 转换结果
        serializable_result = convert_to_serializable(result)

        # 缓存结果
        print(f"【PostgresCache】设置缓存，key: {cache_key}，value类型: {type(serializable_result)}")
        success = await set_cache(cache_key, serializable_result, expire)
        print(f"【PostgresCache】缓存设置结果: {success}")
        return result

    @staticmethod
    def cache_key(prefix: str, *args, **kwargs) -> str:
        """
        生成缓存键

        :param prefix: 缓存键前缀
        :param args: 函数参数
        :param kwargs: 函数关键字参数
        :return: 生成的缓存键
        """
        parts = [prefix]

        # 添加位置参数, 排除数据库会话
        for arg in args:
            if arg is not None and not hasattr(arg, 'execute'):
                parts.append(str(arg))

        # 添加关键字参数
        for key, value in sorted(kwargs.items()):
            if value is not None and key != 'db':
                parts.append(f"{key}:{value}")

        return ":".join(parts)

    @staticmethod
    async def delete(key: str) -> bool:
        """
        删除缓存

        :param key: 缓存键
        :return: 是否删除成功
        """
        try:
            await delete_cache(key)
            return True
        except Exception as e:
            print(f"删除PostgreSQL缓存失败: {e}")
            return False

    @staticmethod
    async def delete_pattern(pattern: str) -> int:
        """
        根据模式删除缓存

        :param pattern: 缓存键模式，支持通配符
        :return: 删除的缓存数量
        """
        try:
            return await delete_cache_pattern(pattern)
        except Exception as e:
            print(f"删除PostgreSQL缓存失败: {e}")
            return 0


def cache_with_postgres(prefix: str, expire: int = 3600):
    """
    PostgreSQL缓存装饰器

    :param prefix: 缓存键前缀
    :param expire: 缓存过期时间(秒)
    :return: 装饰器函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """
        用途：执行decorator相关业务逻辑。

        参数：
        - func（Callable[..., T]）：调用方传入的func数据或控制参数，用于驱动本函数处理流程。

        返回：Callable[..., T]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            """
            用途：异步执行wrapper相关业务流程。

            参数：
            - args（未显式标注）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
            - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            key = PostgresCache.cache_key(prefix, *args, **kwargs)

            return await PostgresCache.get_or_set(key, func, *args, expire=expire, **kwargs)
        return wrapper
    return decorator


DatabaseCache = PostgresCache
cache_with_database = cache_with_postgres

"""
模块职责：项目源码模块，封装 RAGNotebook 的可维护业务逻辑。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from fastapi import HTTPException, Request

from mvc.repositories.runtime_store import hit_rate_limit
from utils.env_loader import load_backend_env, require_env_bool_value


load_backend_env()

# 全局开关：通过环境变量 RATE_LIMIT_ENABLED 控制所有限流是否生效
# 当设置为 false 时，rate_limit 依赖和 RateLimitMiddleware 均直接放行
_RATE_LIMIT_ENABLED = require_env_bool_value("RATE_LIMIT_ENABLED", True)


def rate_limit(limit: int = 1, window: int = 60):
    """
    限流依赖函数
    :param limit: 时间窗口内的最大请求数
    :param window: 时间窗口大小（秒）
    :return: 依赖函数
    """
    async def dependency(request: Request):
        # 全局开关关闭时直接放行，不做任何限流检查
        """
        用途：异步执行dependency相关业务流程。

        参数：
        - request（Request）：调用方传入的request数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if not _RATE_LIMIT_ENABLED:
            return

        # 获取客户端IP
        client_ip = request.client.host
        if not client_ip:
            client_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or 'unknown'

        key = f"rate_limit:aichat:{client_ip}"

        if await hit_rate_limit(key, limit, window):
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后再试"
            )

    return dependency


class RateLimitMiddleware:
    """
    全局限流中间件
    """
    def __init__(self, app, limit: int = 100, window: int = 60):
        """
        用途：执行init相关业务逻辑。

        参数：
        - app（未显式标注）：调用方传入的app数据或控制参数，用于驱动本函数处理流程。
        - limit（int）：调用方传入的limit数据或控制参数，用于驱动本函数处理流程。
        - window（int）：调用方传入的window数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.app = app
        self.limit = limit
        self.window = window

    async def __call__(self, scope, receive, send):
        # 全局开关关闭时直接放行
        """
        用途：异步执行call相关业务流程。

        参数：
        - scope（未显式标注）：调用方传入的scope数据或控制参数，用于驱动本函数处理流程。
        - receive（未显式标注）：调用方传入的receive数据或控制参数，用于驱动本函数处理流程。
        - send（未显式标注）：调用方传入的send数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if not _RATE_LIMIT_ENABLED:
            await self.app(scope, receive, send)
            return

        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # 构建请求对象
        from fastapi import Request
        request = Request(scope, receive)

        # 获取客户端IP
        client_ip = request.client.host
        if not client_ip:
            client_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or 'unknown'

        key = f"rate_limit:global:{client_ip}"

        if await hit_rate_limit(key, self.limit, self.window):
            from starlette.responses import JSONResponse
            response = JSONResponse(
                {"detail": "请求过于频繁，请稍后再试"},
                status_code=429
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

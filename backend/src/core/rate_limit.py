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
        self.app = app
        self.limit = limit
        self.window = window

    async def __call__(self, scope, receive, send):
        # 全局开关关闭时直接放行
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

"""
模块职责：项目源码模块，封装 RAGNotebook 的可维护业务逻辑。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "success", data = None) -> JSONResponse:
    """
    成功响应体
    :param message: 响应消息
    :param data: 响应数据
    :return: JSONResponse
    """
    response = {
        "code": 200,
        "message": message,
        "data": data
    }
    return JSONResponse(content=jsonable_encoder(response))

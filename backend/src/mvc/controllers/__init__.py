"""
模块职责：FastAPI 路由控制器模块，负责请求参数绑定、权限依赖和服务层调用。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from mvc.controllers.chat_controller import chat_router
from mvc.controllers.document_controller import document_router
from mvc.controllers.health_controller import health_router
from mvc.controllers.knowledge_controller import knowledge_router
from mvc.controllers.mindmap_controller import mindmap_router
from mvc.controllers.note_controller import note_router
from mvc.controllers.note_template_controller import note_template_router
from mvc.controllers.project_controller import project_router
from mvc.controllers.quick_test_controller import quick_test_router
from mvc.controllers.user_controller import file_router, user_router

routers = [
    chat_router,
    document_router,
    knowledge_router,
    health_router,
    user_router,
    file_router,
    note_router,
    note_template_router,
    project_router,
    quick_test_router,
    mindmap_router,
]

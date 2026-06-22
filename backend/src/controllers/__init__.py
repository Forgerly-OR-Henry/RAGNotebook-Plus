from controllers.chat_controller import chat_router
from controllers.health_controller import health_router
from controllers.knowledge_controller import knowledge_router
from controllers.mindmap_controller import mindmap_router
from controllers.note_controller import note_router
from controllers.note_template_controller import note_template_router
from controllers.quick_test_controller import quick_test_router
from controllers.review_controller import review_router
from controllers.user_controller import file_router, user_router

routers = [
    chat_router,
    knowledge_router,
    health_router,
    user_router,
    file_router,
    note_router,
    note_template_router,
    review_router,
    quick_test_router,
    mindmap_router,
]

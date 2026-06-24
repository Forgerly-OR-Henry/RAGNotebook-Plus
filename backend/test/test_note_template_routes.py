"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from starlette.routing import Match

from mvc.controllers.note_template_controller import note_template_router


def test_note_template_reorder_route_is_matched_before_template_id_route():
    """
    用途：执行test note template reorder route is matched before template id route相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    scope = {
        "type": "http",
        "method": "PUT",
        "path": "/note-template/reorder",
        "headers": [],
        "query_string": b"",
        "root_path": "",
    }

    for route in note_template_router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            assert route.endpoint.__name__ == "reorder_templates"
            break
    else:
        raise AssertionError("PUT /note-template/reorder did not match any route")

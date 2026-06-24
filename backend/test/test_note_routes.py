"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from starlette.routing import Match

from mvc.controllers.note_controller import note_router


def test_note_auto_tag_route_matches_regenerate_tags_handler():
    """
    用途：执行test note auto tag route matches regenerate tags handler相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/note/test-note-id/auto-tag",
        "headers": [],
        "query_string": b"",
        "root_path": "",
    }

    for route in note_router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            assert route.endpoint.__name__ == "regenerate_tags"
            break
    else:
        raise AssertionError("POST /note/{note_id}/auto-tag did not match any route")

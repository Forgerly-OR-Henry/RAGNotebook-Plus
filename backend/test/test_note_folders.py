"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from starlette.routing import Match

from mvc.controllers.note_controller import note_router
from mvc.models.base import Base
from mvc.models.note_folder import NoteFolder, NoteFolderAssignment
from mvc.schemas import BatchFolderRequest, NoteCreate, NoteFolderCreate, NoteFolderUpdate, NoteUpdate


def _matched_endpoint(path: str, method: str) -> str:
    """
    用途：执行matched endpoint相关业务逻辑。

    参数：
    - path（str）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。
    - method（str）：调用方传入的method数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
        "root_path": "",
    }

    for route in note_router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return route.endpoint.__name__
    raise AssertionError(f"{method} {path} did not match any route")


def test_note_folder_schema_contract():
    """
    用途：执行test note folder schema contract相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    assert NoteFolder.__tablename__ == "note_folders"
    assert NoteFolderAssignment.__tablename__ == "note_folder_assignments"
    assert {"note_folders", "note_folder_assignments"} <= set(Base.metadata.tables)
    assert "uq_note_folder_sibling_name" in {constraint.name for constraint in NoteFolder.__table__.constraints}
    assert "uq_note_folder_assignment_note" in {constraint.name for constraint in NoteFolderAssignment.__table__.constraints}


def test_note_folder_request_contracts():
    """
    用途：执行test note folder request contracts相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    created = NoteCreate(title="标题", content="内容", folder_id="folder-1")
    updated = NoteUpdate(folder_id=None)
    folder = NoteFolderCreate(name="研究", parent_id=None)
    move = NoteFolderUpdate(parent_id="parent-1")
    batch = BatchFolderRequest(ids=["note-1"], folder_id=None)

    assert created.folder_id == "folder-1"
    assert "folder_id" in updated.model_fields_set
    assert folder.name == "研究"
    assert move.parent_id == "parent-1"
    assert batch.folder_id is None


def test_note_folder_routes_match_before_note_id_routes():
    """
    用途：执行test note folder routes match before note id routes相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    assert _matched_endpoint("/note/folders", "GET") == "list_note_folders"
    assert _matched_endpoint("/note/folders", "POST") == "create_note_folder"
    assert _matched_endpoint("/note/folders/folder-1", "PUT") == "update_note_folder"
    assert _matched_endpoint("/note/folders/folder-1", "DELETE") == "delete_note_folder"
    assert _matched_endpoint("/note/batch/folder", "PUT") == "batch_update_folder"

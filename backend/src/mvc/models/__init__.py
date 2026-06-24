"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from mvc.models.base import Base
from mvc.models.chat_history import ChatMessage, ChatSession
from mvc.models.document import Document
from mvc.models.knowledge_document import KnowledgeDocument
from mvc.models.mind_map import MindMap
from mvc.models.note import Note
from mvc.models.note_folder import NoteFolder, NoteFolderAssignment
from mvc.models.knowledge_folder import KnowledgeFolder, KnowledgeFolderAssignment
from mvc.models.note_template import NoteTemplate
from mvc.models.project import ChatProject, ProjectSource
from mvc.models.runtime_state import AppCache, RateLimitCounter, TokenBlacklist
from mvc.models.storage_object import StorageObject
from mvc.models.study_test import StudyTestSession, StudyTestTurn
from mvc.models.user_model import User

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
BACKEND_SRC = BACKEND_DIR / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))
FIXTURE_DIR = BACKEND_DIR / "test" / "fixtures" / "demo_dataset"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"

DEMO_PASSWORD = "demo1234"
REQUIRED_TABLES = (
    "user_service",
    "notes",
    "note_templates",
    "review_records",
    "chat_sessions",
    "chat_messages",
    "study_test_sessions",
    "study_test_turns",
    "mind_maps",
    "knowledge_documents",
    "index_chunks",
)


class SeedError(RuntimeError):
    """Raised for user-actionable demo seed failures."""


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise SeedError(f"Demo manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _items(manifest: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = manifest.get(key, [])
    return value if isinstance(value, list) else []


def _register_id(
    errors: list[str],
    seen: dict[str, str],
    value: Any,
    label: str,
    max_len: int = 36,
) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    if len(value) > max_len:
        errors.append(f"{label} exceeds {max_len} chars: {value}")
    previous = seen.get(value)
    if previous:
        errors.append(f"Duplicate id {value!r}: {previous} and {label}")
    seen[value] = label
    return value


def _validate_required(item: dict[str, Any], fields: tuple[str, ...], label: str, errors: list[str]) -> None:
    for field in fields:
        if field not in item or item[field] in (None, ""):
            errors.append(f"{label} missing required field: {field}")


def _source_exists(source_type: str, source_id: str, note_ids: set[str], knowledge_ids: set[str]) -> bool:
    if source_type == "note":
        return source_id in note_ids
    if source_type == "knowledge":
        return source_id in knowledge_ids
    return source_id in note_ids or source_id in knowledge_ids


def _validate_citations(
    citations: list[dict[str, Any]],
    label: str,
    note_ids: set[str],
    knowledge_ids: set[str],
    errors: list[str],
) -> None:
    for index, citation in enumerate(citations or []):
        citation_label = f"{label}.citations[{index}]"
        _validate_required(citation, ("source_type", "source_id", "title", "quote"), citation_label, errors)
        source_type = citation.get("source_type")
        source_id = citation.get("source_id")
        if isinstance(source_type, str) and isinstance(source_id, str) and not _source_exists(source_type, source_id, note_ids, knowledge_ids):
            errors.append(f"{citation_label} references unknown source: {source_type}:{source_id}")


def validate_manifest(manifest: dict[str, Any], fixture_dir: Path = FIXTURE_DIR) -> list[str]:
    errors: list[str] = []
    seen_ids: dict[str, str] = {}

    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    user = manifest.get("user")
    if not isinstance(user, dict):
        errors.append("user must be an object")
        user = {}
    _validate_required(user, ("id", "username", "email"), "user", errors)
    user_id = _register_id(errors, seen_ids, user.get("id"), "user.id")

    note_ids: set[str] = set()
    for index, note in enumerate(_items(manifest, "notes")):
        label = f"notes[{index}]"
        _validate_required(note, ("id", "title", "content", "category", "tags"), label, errors)
        note_id = _register_id(errors, seen_ids, note.get("id"), f"{label}.id")
        if note_id:
            note_ids.add(note_id)
        if len(str(note.get("title", ""))) > 200:
            errors.append(f"{label}.title exceeds 200 chars")
        if not isinstance(note.get("tags"), list):
            errors.append(f"{label}.tags must be a list")

    knowledge_ids: set[str] = set()
    for index, item in enumerate(_items(manifest, "knowledge_files")):
        label = f"knowledge_files[{index}]"
        _validate_required(item, ("filename", "title"), label, errors)
        filename = item.get("filename")
        if isinstance(filename, str):
            knowledge_ids.add(filename)
            path = fixture_dir / "knowledge" / filename
            if not path.is_file():
                errors.append(f"{label}.filename not found: {path}")
            elif path.stat().st_size == 0:
                errors.append(f"{label}.filename is empty: {path}")

    for index, template in enumerate(_items(manifest, "note_templates")):
        label = f"note_templates[{index}]"
        _validate_required(template, ("id", "name", "content"), label, errors)
        _register_id(errors, seen_ids, template.get("id"), f"{label}.id")

    for index, review in enumerate(_items(manifest, "review_records")):
        label = f"review_records[{index}]"
        _validate_required(review, ("id", "note_id", "review_count", "interval_days", "next_review_days_offset"), label, errors)
        _register_id(errors, seen_ids, review.get("id"), f"{label}.id")
        if review.get("note_id") not in note_ids:
            errors.append(f"{label}.note_id references unknown note: {review.get('note_id')}")

    for index, session in enumerate(_items(manifest, "chat_sessions")):
        label = f"chat_sessions[{index}]"
        _validate_required(session, ("id", "title", "messages"), label, errors)
        _register_id(errors, seen_ids, session.get("id"), f"{label}.id", max_len=64)
        for message_index, message in enumerate(session.get("messages", []) or []):
            msg_label = f"{label}.messages[{message_index}]"
            _validate_required(message, ("role", "content"), msg_label, errors)
            if message.get("role") not in {"user", "assistant"}:
                errors.append(f"{msg_label}.role must be user or assistant")

    for index, session in enumerate(_items(manifest, "quick_test_sessions")):
        label = f"quick_test_sessions[{index}]"
        _validate_required(session, ("id", "source_type", "source_ids", "question_count", "difficulty", "status", "current_turn", "turns"), label, errors)
        _register_id(errors, seen_ids, session.get("id"), f"{label}.id")
        source_type = session.get("source_type")
        for source_id in session.get("source_ids", []) or []:
            if not _source_exists(str(source_type), str(source_id), note_ids, knowledge_ids):
                errors.append(f"{label}.source_ids references unknown source: {source_id}")
        turns = session.get("turns", []) or []
        if len(turns) > int(session.get("question_count") or 0):
            errors.append(f"{label}.turns exceeds question_count")
        _validate_citations(session.get("recommended_refs", []) or [], label, note_ids, knowledge_ids, errors)
        for turn_index, turn in enumerate(turns):
            turn_label = f"{label}.turns[{turn_index}]"
            _validate_required(turn, ("id", "turn_index", "question", "citations"), turn_label, errors)
            _register_id(errors, seen_ids, turn.get("id"), f"{turn_label}.id")
            _validate_citations(turn.get("citations", []) or [], turn_label, note_ids, knowledge_ids, errors)

    for index, mindmap in enumerate(_items(manifest, "mind_maps")):
        label = f"mind_maps[{index}]"
        _validate_required(mindmap, ("id", "title", "source_type", "source_ids", "nodes", "edges"), label, errors)
        _register_id(errors, seen_ids, mindmap.get("id"), f"{label}.id")
        source_type = mindmap.get("source_type")
        for source_id in mindmap.get("source_ids", []) or []:
            if not _source_exists(str(source_type), str(source_id), note_ids, knowledge_ids):
                errors.append(f"{label}.source_ids references unknown source: {source_id}")
        node_ids = {node.get("id") for node in mindmap.get("nodes", []) or [] if isinstance(node, dict)}
        for edge_index, edge in enumerate(mindmap.get("edges", []) or []):
            edge_label = f"{label}.edges[{edge_index}]"
            _validate_required(edge, ("id", "source", "target"), edge_label, errors)
            if edge.get("source") not in node_ids:
                errors.append(f"{edge_label}.source references unknown node: {edge.get('source')}")
            if edge.get("target") not in node_ids:
                errors.append(f"{edge_label}.target references unknown node: {edge.get('target')}")
        _validate_citations(mindmap.get("citations", []) or [], label, note_ids, knowledge_ids, errors)

    if user_id and len(user_id) > 36:
        errors.append("user.id exceeds user_service.uuid length")
    if len(note_ids) < 8:
        errors.append("demo dataset must include at least 8 notes")
    if len(knowledge_ids) < 2:
        errors.append("demo dataset must include at least 2 knowledge files")

    return errors


def load_seed_env() -> None:
    from dotenv import load_dotenv

    from utils.env_loader import resolve_file_backed_secrets

    config_env = REPO_ROOT / "config" / ".env"
    if config_env.is_file():
        load_dotenv(config_env, override=False)
        resolve_file_backed_secrets(config_env)


def validate_environment() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        embedding_dim = int(os.getenv("EMBEDDING_DIM", "1024"))
        if embedding_dim <= 0:
            errors.append("EMBEDDING_DIM must be a positive integer")
    except ValueError:
        errors.append("EMBEDDING_DIM must be a positive integer")

    if not os.getenv("DATABASE_URL"):
        warnings.append("DATABASE_URL is not set; the seed command will rely on POSTGRES_* defaults")
    if not os.getenv("SECRET_KEY") or not os.getenv("ALGORITHM"):
        warnings.append("SECRET_KEY or ALGORITHM is missing; login token generation may fail when the app runs")

    return errors, warnings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _relative_datetime(base: datetime, days_offset: int | float = 0, hours_offset: int | float = 0) -> datetime:
    return base + timedelta(days=days_offset, hours=hours_offset)


def _file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sql_in_params(params: dict[str, Any], prefix: str, values: list[str]) -> str:
    names = []
    for index, value in enumerate(values):
        name = f"{prefix}_{index}"
        params[name] = value
        names.append(f":{name}")
    return ", ".join(names)


async def ensure_schema_available(session) -> None:
    from sqlalchemy import text

    missing = []
    for table in REQUIRED_TABLES:
        result = await session.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table})
        if result.scalar_one_or_none() is None:
            missing.append(table)
    if missing:
        raise SeedError(f"Database schema is missing tables: {', '.join(missing)}. Run Alembic migrations first.")

    result = await session.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
    if not result.scalar():
        raise SeedError("PostgreSQL extension 'vector' is not installed. Run the pgvector migration first.")


async def delete_demo_vectors(session, manifest: dict[str, Any], user_id: str) -> None:
    from sqlalchemy import text

    note_ids = [item["id"] for item in _items(manifest, "notes")]
    filenames = [item["filename"] for item in _items(manifest, "knowledge_files")]

    if note_ids:
        params: dict[str, Any] = {"user_id": user_id}
        note_in = _sql_in_params(params, "note_id", note_ids)
        await session.execute(
            text(
                f"""
                DELETE FROM index_chunks
                WHERE user_id = :user_id
                  AND source_type = 'note'
                  AND (source_id IN ({note_in}) OR metadata ->> 'note_id' IN ({note_in}))
                """
            ),
            params,
        )

    if filenames:
        params = {"user_id": user_id}
        filename_in = _sql_in_params(params, "filename", filenames)
        await session.execute(
            text(
                f"""
                DELETE FROM index_chunks
                WHERE user_id = :user_id
                  AND source_type = 'knowledge'
                  AND (
                    metadata ->> 'original_filename' IN ({filename_in})
                    OR metadata ->> 'filename' IN ({filename_in})
                    OR source_id IN (
                        SELECT id FROM knowledge_documents
                        WHERE user_id = :user_id
                          AND (filename IN ({filename_in}) OR original_filename IN ({filename_in}))
                    )
                  )
                """
            ),
            params,
        )
        await session.execute(
            text(
                f"""
                DELETE FROM knowledge_documents
                WHERE user_id = :user_id
                  AND (filename IN ({filename_in}) OR original_filename IN ({filename_in}))
                """
            ),
            params,
        )


async def reset_demo_data(session, manifest: dict[str, Any], user_id: str) -> None:
    from sqlalchemy import delete

    from models.chat_history import ChatMessage, ChatSession
    from models.mind_map import MindMap
    from models.note import Note
    from models.note_template import NoteTemplate
    from models.review_record import ReviewRecord
    from models.study_test import StudyTestSession, StudyTestTurn

    note_ids = [item["id"] for item in _items(manifest, "notes")]
    template_ids = [item["id"] for item in _items(manifest, "note_templates")]
    review_ids = [item["id"] for item in _items(manifest, "review_records")]
    chat_ids = [item["id"] for item in _items(manifest, "chat_sessions")]
    quick_ids = [item["id"] for item in _items(manifest, "quick_test_sessions")]
    mindmap_ids = [item["id"] for item in _items(manifest, "mind_maps")]

    await delete_demo_vectors(session, manifest, user_id)

    if chat_ids:
        await session.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(chat_ids)))
        await session.execute(delete(ChatSession).where(ChatSession.user_id == user_id, ChatSession.id.in_(chat_ids)))
    if quick_ids:
        await session.execute(delete(StudyTestTurn).where(StudyTestTurn.user_id == user_id, StudyTestTurn.session_id.in_(quick_ids)))
        await session.execute(delete(StudyTestSession).where(StudyTestSession.user_id == user_id, StudyTestSession.id.in_(quick_ids)))
    if mindmap_ids:
        await session.execute(delete(MindMap).where(MindMap.user_id == user_id, MindMap.id.in_(mindmap_ids)))
    if review_ids:
        await session.execute(delete(ReviewRecord).where(ReviewRecord.user_id == user_id, ReviewRecord.id.in_(review_ids)))
    if template_ids:
        await session.execute(delete(NoteTemplate).where(NoteTemplate.user_id == user_id, NoteTemplate.id.in_(template_ids)))
    if note_ids:
        await session.execute(delete(Note).where(Note.user_id == user_id, Note.id.in_(note_ids)))


def _assert_owned(obj: Any, user_id: str, label: str) -> None:
    owner = getattr(obj, "user_id", user_id)
    if owner != user_id:
        raise SeedError(f"{label} already exists but belongs to another user: {owner}")


async def ensure_demo_user(session, user_config: dict[str, Any]) -> str:
    from sqlalchemy import or_, select

    from models.user_model import User, UserStatusChoice
    from utils.auth_utils import hash_password, verify_password

    user_id = user_config["id"]
    username = user_config["username"]
    email = user_config["email"]
    result = await session.execute(select(User).where(or_(User.uuid == user_id, User.username == username, User.email == email)))
    matches = result.scalars().all()
    if len({user.uuid for user in matches}) > 1:
        raise SeedError("demo_user username/email collides with multiple existing users")

    user = matches[0] if matches else None
    if user and user.uuid != user_id:
        raise SeedError(f"demo_user already exists with unexpected id {user.uuid}; expected {user_id}")

    if not user:
        user = User(uuid=user_id)
        session.add(user)

    user.username = username
    user.email = email
    user.telephone = user_config.get("telephone")
    user.status = UserStatusChoice.ACTIVE
    user.is_active = True
    user.bio = user_config.get("bio")
    user.gender = user_config.get("gender")
    if not user.password or not verify_password(DEMO_PASSWORD, user.password):
        user.password = hash_password(DEMO_PASSWORD)

    return user_id


async def upsert_notes(session, manifest: dict[str, Any], user_id: str, base_time: datetime) -> None:
    from models.note import Note

    for item in _items(manifest, "notes"):
        note = await session.get(Note, item["id"])
        if note:
            _assert_owned(note, user_id, f"note {item['id']}")
        else:
            note = Note(id=item["id"], user_id=user_id)
            session.add(note)

        note.title = item["title"]
        note.content = item["content"]
        note.category = item.get("category")
        note.tags = item.get("tags", [])
        note.is_pinned = bool(item.get("is_pinned", False))
        note.created_at = _relative_datetime(base_time, days_offset=-int(item.get("created_days_ago", 0)))
        note.updated_at = _relative_datetime(base_time, hours_offset=-int(item.get("updated_hours_ago", 0)))


async def upsert_note_templates(session, manifest: dict[str, Any], user_id: str, base_time: datetime) -> None:
    from models.note_template import NoteTemplate

    for index, item in enumerate(_items(manifest, "note_templates")):
        template = await session.get(NoteTemplate, item["id"])
        if template:
            _assert_owned(template, user_id, f"note_template {item['id']}")
        else:
            template = NoteTemplate(id=item["id"], user_id=user_id)
            session.add(template)

        template.name = item["name"]
        template.icon = item.get("icon", "FileText")
        template.category = item.get("category", "")
        template.title = item.get("title", "")
        template.content = item.get("content", "")
        template.tags = item.get("tags", [])
        template.is_default = False
        template.sort_order = int(item.get("sort_order", index + 100))
        template.created_at = _relative_datetime(base_time, days_offset=-5)
        template.updated_at = base_time


async def upsert_review_records(session, manifest: dict[str, Any], user_id: str, base_time: datetime) -> None:
    from models.review_record import ReviewRecord

    for item in _items(manifest, "review_records"):
        record = await session.get(ReviewRecord, item["id"])
        if record:
            _assert_owned(record, user_id, f"review_record {item['id']}")
        else:
            record = ReviewRecord(id=item["id"], user_id=user_id)
            session.add(record)

        last_review_offset = item.get("last_review_days_ago")
        record.note_id = item["note_id"]
        record.review_count = int(item.get("review_count", 0))
        record.interval_days = int(item.get("interval_days", 1))
        record.last_reviewed_at = None if last_review_offset is None else _relative_datetime(base_time, days_offset=-int(last_review_offset))
        record.next_review_at = _relative_datetime(base_time, days_offset=int(item.get("next_review_days_offset", 0)))
        record.created_at = _relative_datetime(base_time, days_offset=-10)


async def upsert_chat_sessions(session, manifest: dict[str, Any], user_id: str, base_time: datetime) -> None:
    from sqlalchemy import delete

    from models.chat_history import ChatMessage, ChatSession

    chat_ids = [item["id"] for item in _items(manifest, "chat_sessions")]
    for chat_id in chat_ids:
        existing = await session.get(ChatSession, chat_id)
        if existing:
            _assert_owned(existing, user_id, f"chat_session {chat_id}")
    if chat_ids:
        await session.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(chat_ids)))

    for index, item in enumerate(_items(manifest, "chat_sessions")):
        chat = await session.get(ChatSession, item["id"])
        if not chat:
            chat = ChatSession(id=item["id"], user_id=user_id)
            session.add(chat)
        chat.title = item["title"]
        chat.metadata_ = item.get("metadata", {"dataset": "demo"})
        chat.created_at = _relative_datetime(base_time, days_offset=-(index + 2))
        chat.updated_at = _relative_datetime(base_time, hours_offset=-index)

        for message_index, message in enumerate(item.get("messages", []) or []):
            session.add(
                ChatMessage(
                    session_id=item["id"],
                    role=message["role"],
                    content=message["content"],
                    metadata_=message.get("metadata", {"dataset": "demo"}),
                    created_at=_relative_datetime(base_time, days_offset=-(index + 2), hours_offset=message_index),
                )
            )


async def upsert_quick_tests(session, manifest: dict[str, Any], user_id: str, base_time: datetime) -> None:
    from sqlalchemy import delete

    from models.study_test import StudyTestSession, StudyTestTurn

    session_ids = [item["id"] for item in _items(manifest, "quick_test_sessions")]
    for session_id in session_ids:
        existing = await session.get(StudyTestSession, session_id)
        if existing:
            _assert_owned(existing, user_id, f"quick_test_session {session_id}")

    if session_ids:
        await session.execute(delete(StudyTestTurn).where(StudyTestTurn.user_id == user_id, StudyTestTurn.session_id.in_(session_ids)))

    for index, item in enumerate(_items(manifest, "quick_test_sessions")):
        test_session = await session.get(StudyTestSession, item["id"])
        if not test_session:
            test_session = StudyTestSession(id=item["id"], user_id=user_id)
            session.add(test_session)

        test_session.source_type = item["source_type"]
        test_session.source_ids = item.get("source_ids", [])
        test_session.question_count = int(item.get("question_count", 1))
        test_session.difficulty = item.get("difficulty", "normal")
        test_session.focus = item.get("focus")
        test_session.status = item.get("status", "active")
        test_session.current_turn = int(item.get("current_turn", 1))
        test_session.summary = item.get("summary")
        test_session.weak_points = item.get("weak_points", [])
        test_session.recommended_refs = item.get("recommended_refs", [])
        test_session.created_at = _relative_datetime(base_time, days_offset=-(index + 1))
        test_session.updated_at = base_time
        test_session.completed_at = base_time if item.get("status") == "completed" else None

        for turn in item.get("turns", []) or []:
            existing_turn = await session.get(StudyTestTurn, turn["id"])
            if existing_turn and existing_turn.user_id != user_id:
                raise SeedError(f"study_test_turn {turn['id']} already exists but belongs to another user")
            session.add(
                StudyTestTurn(
                    id=turn["id"],
                    session_id=item["id"],
                    user_id=user_id,
                    turn_index=int(turn["turn_index"]),
                    question=turn["question"],
                    answer=turn.get("answer"),
                    feedback=turn.get("feedback"),
                    score=turn.get("score"),
                    citations=turn.get("citations", []),
                    created_at=_relative_datetime(base_time, days_offset=-(index + 1), hours_offset=int(turn["turn_index"])),
                )
            )


async def upsert_mind_maps(session, manifest: dict[str, Any], user_id: str, base_time: datetime) -> None:
    from models.mind_map import MindMap

    for index, item in enumerate(_items(manifest, "mind_maps")):
        mindmap = await session.get(MindMap, item["id"])
        if mindmap:
            _assert_owned(mindmap, user_id, f"mind_map {item['id']}")
        else:
            mindmap = MindMap(id=item["id"], user_id=user_id)
            session.add(mindmap)

        mindmap.title = item["title"]
        mindmap.source_type = item["source_type"]
        mindmap.source_ids = item.get("source_ids", [])
        mindmap.focus = item.get("focus")
        mindmap.graph = {"nodes": item.get("nodes", []), "edges": item.get("edges", [])}
        mindmap.citations = item.get("citations", [])
        mindmap.source_refs = item.get("source_refs", [])
        mindmap.model_config = item.get("model_config", {"seeded": True})
        mindmap.version = int(item.get("version", 1))
        mindmap.created_at = _relative_datetime(base_time, days_offset=-(index + 3))
        mindmap.updated_at = base_time


async def build_embed_model():
    from ai.rag.vector_store import embedding_dimension
    from utils.factory import EmbedModelFactory

    model = EmbedModelFactory().generator()
    try:
        sample = await asyncio.to_thread(model.embed_query, "RAGNotebook demo seed embedding dimension check")
    except Exception as exc:
        raise SeedError(f"Embedding model check failed: {exc}") from exc

    actual = len(sample or [])
    expected = embedding_dimension()
    if actual != expected:
        raise SeedError(f"EMBEDDING_DIM={expected} does not match embedding model output dimension {actual}")
    return model


async def sync_note_vectors(manifest: dict[str, Any], user_id: str, embed_model) -> None:
    from langchain_core.documents import Document

    from repositories.index_repository import IndexRepository

    notes = _items(manifest, "notes")
    note_ids = [item["id"] for item in notes]
    if not note_ids:
        return

    repository = IndexRepository(embedding_model=embed_model)
    for item in notes:
        await repository.delete_source(user_id=user_id, source_type="note", source_id=item["id"])
        await repository.upsert_documents(
            source_type="note",
            source_id=item["id"],
            user_id=user_id,
            documents=[
                Document(
                    page_content=item["content"],
                    metadata={
                        "note_id": item["id"],
                        "doc_type": "note",
                        "title": item["title"],
                        "dataset": "demo",
                    },
                )
            ],
            metadata={"note_id": item["id"], "title": item["title"], "dataset": "demo"},
        )


async def _existing_knowledge_md5(session, user_id: str, filename: str) -> str | None:
    from sqlalchemy import text

    result = await session.execute(
        text(
            """
            SELECT md5
            FROM knowledge_documents
            WHERE user_id = :user_id
              AND (filename = :filename OR original_filename = :filename)
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"user_id": user_id, "filename": filename},
    )
    return result.scalar_one_or_none()


async def clear_knowledge_file(session, user_id: str, filename: str) -> None:
    from sqlalchemy import text

    await session.execute(
        text(
            """
            DELETE FROM index_chunks
            WHERE user_id = :user_id
              AND source_type = 'knowledge'
              AND (
                metadata ->> 'original_filename' = :filename
                OR metadata ->> 'filename' = :filename
                OR source_id IN (
                    SELECT id FROM knowledge_documents
                    WHERE user_id = :user_id
                      AND (filename = :filename OR original_filename = :filename)
                )
              )
            """
        ),
        {"user_id": user_id, "filename": filename},
    )
    await session.execute(
        text(
            """
            DELETE FROM knowledge_documents
            WHERE user_id = :user_id
              AND (filename = :filename OR original_filename = :filename)
            """
        ),
        {"user_id": user_id, "filename": filename},
    )


async def sync_knowledge_files(manifest: dict[str, Any], user_id: str, embed_model) -> None:
    from starlette.datastructures import UploadFile

    from core.background_init import init_manager
    from db.db_config import AsyncSessionLocal
    from services.knowledge_service import KnowledgeIngestionService

    init_manager.embed_model = embed_model
    init_manager.models_ready.set()

    ingestion_service = KnowledgeIngestionService()
    for item in _items(manifest, "knowledge_files"):
        filename = item["filename"]
        path = FIXTURE_DIR / "knowledge" / filename
        current_md5 = _file_md5(path)

        async with AsyncSessionLocal() as session:
            existing_md5 = await _existing_knowledge_md5(session, user_id, filename)
            if existing_md5 == current_md5:
                print(f"Knowledge fixture unchanged, skipped: {filename}")
                continue
            await clear_knowledge_file(session, user_id, filename)
            await session.commit()

        with path.open("rb") as handle:
            upload = UploadFile(file=handle, filename=filename)
            async for _ in ingestion_service.upload_stream([upload], user_id=user_id):
                pass
        print(f"Knowledge fixture processed: {filename}")


async def seed_database(manifest: dict[str, Any], reset_demo: bool, skip_knowledge: bool) -> None:
    from db.db_config import AsyncSessionLocal

    base_time = _now()
    user_id = manifest["user"]["id"]

    async with AsyncSessionLocal() as session:
        await ensure_schema_available(session)
        if reset_demo:
            await reset_demo_data(session, manifest, user_id)
            await session.commit()

        user_id = await ensure_demo_user(session, manifest["user"])
        await upsert_notes(session, manifest, user_id, base_time)
        await upsert_note_templates(session, manifest, user_id, base_time)
        await upsert_review_records(session, manifest, user_id, base_time)
        await upsert_chat_sessions(session, manifest, user_id, base_time)
        await upsert_quick_tests(session, manifest, user_id, base_time)
        await upsert_mind_maps(session, manifest, user_id, base_time)
        await session.commit()

    if skip_knowledge:
        print("Skipped knowledge fixtures and all vector synchronization because --skip-knowledge was set.")
        return

    embed_model = await build_embed_model()
    await sync_note_vectors(manifest, user_id, embed_model)
    await sync_knowledge_files(manifest, user_id, embed_model)


def print_manifest_summary(manifest: dict[str, Any]) -> None:
    print(
        "Demo dataset: "
        f"{len(_items(manifest, 'notes'))} notes, "
        f"{len(_items(manifest, 'knowledge_files'))} knowledge files, "
        f"{len(_items(manifest, 'chat_sessions'))} chat sessions, "
        f"{len(_items(manifest, 'quick_test_sessions'))} quick-test sessions, "
        f"{len(_items(manifest, 'mind_maps'))} mind maps"
    )


async def run(args: argparse.Namespace) -> None:
    load_seed_env()
    manifest = load_manifest()

    errors = validate_manifest(manifest)
    env_errors, warnings = validate_environment()
    errors.extend(env_errors)
    if errors:
        raise SeedError("Demo dataset validation failed:\n- " + "\n- ".join(errors))

    for warning in warnings:
        print(f"Warning: {warning}")
    print_manifest_summary(manifest)

    if args.dry_run:
        print("Dry run passed. No database writes or model calls were performed.")
        return

    await seed_database(manifest, reset_demo=args.reset_demo, skip_knowledge=args.skip_knowledge)
    print(f"Demo seed completed. Login with {manifest['user']['username']} / {DEMO_PASSWORD}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed the local RAGNotebook demo dataset.")
    parser.add_argument("--dry-run", action="store_true", help="Validate fixtures and environment without database writes or model calls.")
    parser.add_argument("--reset-demo", action="store_true", help="Delete only the fixed demo dataset rows before reseeding.")
    parser.add_argument("--skip-knowledge", action="store_true", help="Skip knowledge fixtures and all vector synchronization.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        asyncio.run(run(args))
    except SeedError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

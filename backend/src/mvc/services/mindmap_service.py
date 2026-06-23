from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mvc.agent_gateway.mindmap_ai_gateway import model_json
from mvc.models.mind_map import MindMap
from mvc.schemas import MindMapGenerateRequest, MindMapUpdateRequest
from mvc.services.sources import SourceChunk, format_source_context, get_source_registry


class MindMapService:
    def __init__(self):
        self.collector = get_source_registry()

    async def generate(self, db: AsyncSession, user_id: str, payload: MindMapGenerateRequest) -> dict:
        source_ids = self._unique_ids(payload.source_ids)
        chunks = await self.collector.collect(db, user_id, payload.source_type, source_ids, max_chunks=30)
        if not chunks:
            raise ValueError("没有找到可用于生成思维导图的来源内容")

        graph = await self._generate_graph(chunks, payload.max_nodes, payload.max_depth, payload.focus)
        citations = [chunk.citation() for chunk in chunks[:5]]
        source_refs = [{"id": chunk.source_id, "type": chunk.source_type, "title": chunk.title} for chunk in chunks]
        mindmap_id = str(uuid.uuid4())
        mindmap = MindMap(
            id=mindmap_id,
            user_id=user_id,
            title=graph["title"],
            source_type=payload.source_type,
            source_ids=source_ids,
            focus=payload.focus,
            graph={"nodes": graph["nodes"], "edges": graph["edges"]},
            citations=citations,
            source_refs=source_refs,
            model_config={"max_nodes": payload.max_nodes, "max_depth": payload.max_depth},
            version=1,
        )
        db.add(mindmap)
        await db.commit()
        return self._to_response(mindmap)

    def _unique_ids(self, source_ids: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for source_id in source_ids:
            if not source_id or source_id in seen:
                continue
            seen.add(source_id)
            unique.append(source_id)
        return unique

    async def get(self, db: AsyncSession, user_id: str, mindmap_id: str) -> dict | None:
        mindmap = await self._get_orm(db, user_id, mindmap_id)
        return self._to_response(mindmap) if mindmap else None

    async def update(self, db: AsyncSession, user_id: str, mindmap_id: str, payload: MindMapUpdateRequest) -> dict | None:
        mindmap = await self._get_orm(db, user_id, mindmap_id)
        if not mindmap:
            return None
        mindmap.title = payload.title
        mindmap.graph = {
            "nodes": [node.model_dump() for node in payload.nodes],
            "edges": [edge.model_dump() for edge in payload.edges],
        }
        mindmap.version += 1
        await db.commit()
        await db.refresh(mindmap)
        return self._to_response(mindmap)

    async def export(self, db: AsyncSession, user_id: str, mindmap_id: str, export_format: str) -> str | dict | None:
        mindmap = await self._get_orm(db, user_id, mindmap_id)
        if not mindmap:
            return None
        graph = mindmap.graph or {"nodes": [], "edges": []}
        if export_format == "json":
            return {
                "title": mindmap.title,
                "nodes": graph.get("nodes", []),
                "edges": graph.get("edges", []),
                "citations": mindmap.citations or [],
            }
        return self._to_mermaid(mindmap.title, graph.get("nodes", []), graph.get("edges", []))

    async def _get_orm(self, db: AsyncSession, user_id: str, mindmap_id: str):
        result = await db.execute(select(MindMap).where(MindMap.id == mindmap_id, MindMap.user_id == user_id))
        return result.scalar_one_or_none()

    async def _model_json(self, prompt: str) -> dict | None:
        return await model_json(prompt)

    async def _generate_graph(self, chunks: list[SourceChunk], max_nodes: int, max_depth: int, focus: str | None) -> dict:
        max_nodes = max(5, min(max_nodes, 80))
        max_depth = max(2, min(max_depth, 6))
        context = format_source_context(chunks, max_chars=16000)
        prompt = f"""请从资料中抽取一张交互式思维导图。
关注点: {focus or "核心概念和关系"}
节点上限: {max_nodes}
深度上限: {max_depth}
资料:
{context}

只返回 JSON:
{{
  "title": "导图标题",
  "nodes": [{{"id": "n1", "label": "主题", "level": 0, "type": "root", "summary": "一句话说明", "source_refs": []}}],
  "edges": [{{"id": "e1", "source": "n1", "target": "n2", "label": "包含"}}]
}}"""
        data = await self._model_json(prompt)
        if data and data.get("nodes") and data.get("edges"):
            return {
                "title": str(data.get("title") or chunks[0].title),
                "nodes": data["nodes"][:max_nodes],
                "edges": data["edges"],
            }
        return self._fallback_graph(chunks, max_nodes)

    def _fallback_graph(self, chunks: list[SourceChunk], max_nodes: int) -> dict:
        title = chunks[0].title if len(chunks) == 1 else "多来源知识导图"
        nodes = [{"id": "n0", "label": title[:40], "level": 0, "type": "root", "summary": "自动生成的中心主题", "source_refs": []}]
        edges = []
        node_index = 1
        for chunk in chunks:
            if node_index >= max_nodes:
                break
            source_node_id = f"n{node_index}"
            nodes.append(
                {
                    "id": source_node_id,
                    "label": chunk.title[:50],
                    "level": 1,
                    "type": chunk.source_type,
                    "summary": "来源内容",
                    "source_refs": [chunk.source_id],
                }
            )
            edges.append({"id": f"e{node_index}", "source": "n0", "target": source_node_id, "label": "包含"})
            node_index += 1

            lines = [line.strip("# -\t ") for line in chunk.content.splitlines() if line.strip()]
            candidates = [line for line in lines if 4 <= len(line) <= 60][:4]
            if not candidates:
                candidates = [chunk.content.strip()[:40] or chunk.title]
            for candidate in candidates:
                if node_index >= max_nodes:
                    break
                node_id = f"n{node_index}"
                nodes.append(
                    {
                        "id": node_id,
                        "label": candidate,
                        "level": 2,
                        "type": "concept",
                        "summary": f"来源：{chunk.title}",
                        "source_refs": [chunk.source_id],
                    }
                )
                edges.append({"id": f"e{node_index}", "source": source_node_id, "target": node_id, "label": "要点"})
                node_index += 1
        return {"title": title, "nodes": nodes, "edges": edges}

    def _to_response(self, mindmap: MindMap) -> dict:
        graph = mindmap.graph or {"nodes": [], "edges": []}
        return {
            "mindmap_id": mindmap.id,
            "title": mindmap.title,
            "source_type": mindmap.source_type,
            "source_ids": mindmap.source_ids or [],
            "nodes": graph.get("nodes", []),
            "edges": graph.get("edges", []),
            "citations": mindmap.citations or [],
            "source_refs": mindmap.source_refs or [],
            "version": mindmap.version,
        }

    def _to_mermaid(self, title: str, nodes: list[dict], edges: list[dict]) -> str:
        labels = {node["id"]: node.get("label", node["id"]).replace('"', "'") for node in nodes}
        lines = [f"%% {title}", "mindmap"]
        root = nodes[0]["id"] if nodes else "root"
        lines.append(f"  root(({labels.get(root, title)}))")
        for edge in edges:
            target = edge.get("target")
            if target in labels:
                lines.append(f"    {labels[target]}")
        return "\n".join(lines)

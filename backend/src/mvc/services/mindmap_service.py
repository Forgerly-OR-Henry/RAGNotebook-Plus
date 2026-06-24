"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mvc.agent_gateway.mindmap_ai_gateway import model_json
from mvc.models.mind_map import MindMap
from mvc.schemas import MindMapGenerateRequest, MindMapUpdateRequest
from mvc.services.sources import SourceChunk, format_source_context, get_source_registry


class MindMapService:
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：
    - collector（实例属性，由构造函数注入或初始化）：保存collector相关状态、配置或数据字段。
    """
    def __init__(self):
        """
        用途：执行init相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.collector = get_source_registry()

    async def generate(self, db: AsyncSession, user_id: str, payload: MindMapGenerateRequest) -> dict:
        """
        用途：异步执行generate相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - payload（MindMapGenerateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：执行unique ids相关业务逻辑。

        参数：
        - source_ids（list[str]）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。

        返回：list[str]；返回值供调用方继续编排业务流程或生成接口响应。
        """
        seen: set[str] = set()
        unique: list[str] = []
        for source_id in source_ids:
            if not source_id or source_id in seen:
                continue
            seen.add(source_id)
            unique.append(source_id)
        return unique

    async def get(self, db: AsyncSession, user_id: str, mindmap_id: str) -> dict | None:
        """
        用途：异步执行get相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - mindmap_id（str）：调用方传入的mindmap_id数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        mindmap = await self._get_orm(db, user_id, mindmap_id)
        return self._to_response(mindmap) if mindmap else None

    async def update(self, db: AsyncSession, user_id: str, mindmap_id: str, payload: MindMapUpdateRequest) -> dict | None:
        """
        用途：异步执行update相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - mindmap_id（str）：调用方传入的mindmap_id数据或控制参数，用于驱动本函数处理流程。
        - payload（MindMapUpdateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：异步执行export相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - mindmap_id（str）：调用方传入的mindmap_id数据或控制参数，用于驱动本函数处理流程。
        - export_format（str）：调用方传入的export_format数据或控制参数，用于驱动本函数处理流程。

        返回：str | dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：读取或查询get orm相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - mindmap_id（str）：调用方传入的mindmap_id数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        result = await db.execute(select(MindMap).where(MindMap.id == mindmap_id, MindMap.user_id == user_id))
        return result.scalar_one_or_none()

    async def _model_json(self, prompt: str) -> dict | None:
        """
        用途：异步执行model json相关业务流程。

        参数：
        - prompt（str）：调用方传入的prompt数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return await model_json(prompt)

    async def _generate_graph(self, chunks: list[SourceChunk], max_nodes: int, max_depth: int, focus: str | None) -> dict:
        """
        用途：生成generate graph相关的数据或流程。

        参数：
        - chunks（list[SourceChunk]）：调用方传入的chunks数据或控制参数，用于驱动本函数处理流程。
        - max_nodes（int）：调用方传入的max_nodes数据或控制参数，用于驱动本函数处理流程。
        - max_depth（int）：调用方传入的max_depth数据或控制参数，用于驱动本函数处理流程。
        - focus（str | None）：调用方传入的focus数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：执行fallback graph相关业务逻辑。

        参数：
        - chunks（list[SourceChunk]）：调用方传入的chunks数据或控制参数，用于驱动本函数处理流程。
        - max_nodes（int）：调用方传入的max_nodes数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
        """
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
        """
        用途：执行to response相关业务逻辑。

        参数：
        - mindmap（MindMap）：调用方传入的mindmap数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
        """
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
        """
        用途：执行to mermaid相关业务逻辑。

        参数：
        - title（str）：调用方传入的title数据或控制参数，用于驱动本函数处理流程。
        - nodes（list[dict]）：调用方传入的nodes数据或控制参数，用于驱动本函数处理流程。
        - edges（list[dict]）：调用方传入的edges数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        labels = {node["id"]: node.get("label", node["id"]).replace('"', "'") for node in nodes}
        lines = [f"%% {title}", "mindmap"]
        root = nodes[0]["id"] if nodes else "root"
        lines.append(f"  root(({labels.get(root, title)}))")
        for edge in edges:
            target = edge.get("target")
            if target in labels:
                lines.append(f"    {labels[target]}")
        return "\n".join(lines)

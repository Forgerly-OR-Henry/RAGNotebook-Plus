from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourceChunk:
    source_type: str
    source_id: str
    title: str
    content: str
    chunk_id: str | None = None
    score: float | None = None

    def citation(self) -> dict:
        quote = self.content.strip().replace("\n", " ")
        if len(quote) > 220:
            quote = quote[:220] + "..."
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "title": self.title,
            "chunk_id": self.chunk_id,
            "quote": quote,
            "score": self.score,
        }


def format_source_context(chunks: list[SourceChunk], max_chars: int = 8000) -> str:
    parts = []
    total = 0
    for idx, chunk in enumerate(chunks, 1):
        item = f"[{idx}] 来源:{chunk.source_type} 标题:{chunk.title}\n{chunk.content.strip()}\n"
        if total + len(item) > max_chars:
            break
        parts.append(item)
        total += len(item)
    return "\n".join(parts)

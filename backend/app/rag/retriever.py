"""RAG 检索：从本地知识库（KnowledgeChunk 表）做混合检索，供诊断与问答溯源。"""
from __future__ import annotations
from app.models import KnowledgeChunk, KnowledgeDoc
from app.rag.vectorstore import hybrid_search


async def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    """检索知识库，返回命中条目（含 score、title、content）。"""
    rows = await KnowledgeChunk.all().limit(2000)
    if not rows:
        return []
    # 批量取标题
    doc_ids = list({r.doc_id for r in rows})
    docs = {d.id: d.title for d in await KnowledgeDoc.filter(id__in=doc_ids)}
    chunks = [{
        "id": r.id,
        "doc_id": r.doc_id,
        "title": docs.get(r.doc_id, ""),
        "content": r.content,
        "embedding": r.embedding or [],
        "tokens": r.tokens or [],
    } for r in rows]
    hits = hybrid_search(query, chunks, top_k)
    return [{"chunk_id": h["id"], "doc_id": h["doc_id"], "title": h["title"],
             "content": h["content"], "score": h["score"]} for h in hits]


def format_refs(hits: list[dict]) -> str:
    """把命中项格式化为提示词上下文。"""
    if not hits:
        return ""
    parts = []
    for i, h in enumerate(hits, 1):
        parts.append(f"[{i}] 《{h['title']}》(相关度 {h['score']}): {h['content'][:300]}")
    return "\n".join(parts)

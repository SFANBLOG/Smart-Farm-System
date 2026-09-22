"""本地向量库：确定性哈希嵌入 + 余弦/关键词混合打分。不依赖任何外部向量数据库。"""
from __future__ import annotations
import hashlib
import math
import re
from app.config import settings

DIM = 128


def hash_embedding(text: str, dim: int = DIM) -> list[float]:
    """确定性哈希向量：同一内容稳定命中。用多轮 md5 把词袋投影到 dim 维。"""
    vec = [0.0] * dim
    tokens = tokenize(text)
    if not tokens:
        return vec
    for tok in tokens:
        h = hashlib.md5(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "big") % dim
        sign = 1.0 if h[4] % 2 == 0 else -1.0
        weight = int.from_bytes(h[5:9], "big") % 100 / 100.0 + 0.1
        vec[idx] += sign * weight
    # L2 归一化
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def tokenize(text: str) -> list[str]:
    """中英文混合切词：中文按 bigram，英文按单词。"""
    text = (text or "").lower()
    words = re.findall(r"[a-zA-Z]+|\d+", text)
    han = re.findall(r"[\u4e00-\u9fff]", text)
    bigrams = [han[i] + han[i + 1] for i in range(len(han) - 1)]
    return words + han + bigrams


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return dot  # 已归一化


def keyword_score(query_tokens: set[str], doc_tokens: list[str]) -> float:
    if not query_tokens:
        return 0.0
    hits = sum(1 for t in set(doc_tokens) if t in query_tokens)
    return hits / len(query_tokens)


def hybrid_search(query: str, chunks: list[dict], top_k: int | None = None) -> list[dict]:
    """chunks: [{id, doc_id, title, content, embedding, tokens}]。返回带 score 的命中列表。"""
    top_k = top_k or settings.RAG_TOP_K
    q_emb = hash_embedding(query)
    q_tokens = set(tokenize(query))
    scored = []
    for c in chunks:
        emb = c.get("embedding") or []
        cos = cosine(q_emb, emb)
        kw = keyword_score(q_tokens, c.get("tokens") or tokenize(c.get("content", "")))
        score = 0.6 * cos + 0.4 * kw
        scored.append({**c, "score": round(score, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return [s for s in scored[:top_k] if s["score"] > 0.02]


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    """按字符切片，带重叠。"""
    size = size or settings.RAG_CHUNK_SIZE
    overlap = overlap or settings.RAG_CHUNK_OVERLAP
    text = (text or "").strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks

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


STOPWORDS = {"怎么", "怎样", "如何", "什么", "哪些", "哪个", "多少", "为什么", "请问",
             "帮我", "一下", "需要", "可以", "应该", "是否", "有没有", "怎么办"}
STOP_CHARS = set("怎么吗呢吧啥的了呀么")


def _content_tokens(tokens: list[str]) -> list[str]:
    """过滤疑问/虚词，只保留有判别力的词元。"""
    return [t for t in tokens if t not in STOPWORDS and t not in STOP_CHARS]


def keyword_score(query_tokens: set[str], doc_tokens: list[str]) -> float:
    """加权覆盖率：bigram 权重 2（更具判别力），单字/英文词权重 1。"""
    if not query_tokens:
        return 0.0
    doc_set = set(doc_tokens)
    weight = sum(2 if len(t) >= 2 else 1 for t in query_tokens if t in doc_set)
    total = sum(2 if len(t) >= 2 else 1 for t in query_tokens)
    return weight / total if total else 0.0


def char_score(query: str, doc_text: str) -> float:
    """字符级覆盖：查询实义汉字在文档中的出现比例，对短查询更稳健。"""
    q_chars = {c for c in re.findall(r"[\u4e00-\u9fff]", query) if c not in STOP_CHARS}
    if not q_chars:
        return 0.0
    return len(q_chars & set(doc_text)) / len(q_chars)


def hybrid_search(query: str, chunks: list[dict], top_k: int | None = None) -> list[dict]:
    """chunks: [{id, doc_id, title, content, embedding, tokens}]。返回带 score 的命中列表。"""
    top_k = top_k or settings.RAG_TOP_K
    q_emb = hash_embedding(query)
    q_tokens = set(_content_tokens(tokenize(query)))
    scored = []
    for c in chunks:
        emb = c.get("embedding") or []
        cos = cosine(q_emb, emb)
        doc_tokens = c.get("tokens") or tokenize(c.get("content", ""))
        kw = 0.5 * keyword_score(q_tokens, doc_tokens) + 0.5 * char_score(query, c.get("content", ""))
        # 哈希余弦噪声大，仅作辅助信号；关键词/字符覆盖为主
        raw = 0.15 * max(cos, 0.0) + 0.85 * kw
        # 平方根校准：抬升中高段命中，避免展示分普遍偏低
        score = math.sqrt(raw) if raw > 0 else 0.0
        scored.append({**c, "score": round(score, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    # 单文档最多贡献 2 块，保证引用来源多样
    picked, per_doc = [], {}
    for s in scored:
        if s["score"] <= 0.05:
            break
        did = s.get("doc_id")
        if per_doc.get(did, 0) >= 2:
            continue
        per_doc[did] = per_doc.get(did, 0) + 1
        picked.append(s)
        if len(picked) >= top_k:
            break
    return picked


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    """按句界切片：整句贪心装填至 size，段间以整句承接约 overlap，避免截断句子；超长单句回退定长窗口。"""
    size = size or settings.RAG_CHUNK_SIZE
    overlap = overlap or settings.RAG_CHUNK_OVERLAP
    text = (text or "").strip()
    if not text:
        return []
    sents = [p for p in re.split(r"(?<=[。！？；\n])", text) if p.strip()]
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0

    def flush_with_carry():
        nonlocal cur, cur_len
        chunks.append("".join(cur))
        carry: list[str] = []
        c_len = 0
        for x in reversed(cur):
            if c_len + len(x) > overlap:
                break
            carry.insert(0, x)
            c_len += len(x)
        cur, cur_len = carry, c_len

    for s in sents:
        if len(s) > size:  # 超长单句：定长硬切兜底，不与前后句做整句承接
            if cur:
                flush_with_carry()
            cur, cur_len = [], 0
            step = size - overlap if overlap < size else size
            while len(s) > size:
                chunks.append(s[:size])
                s = s[step:]
            if s.strip():
                cur, cur_len = [s], len(s)
            continue
        if cur and cur_len + len(s) > size:
            flush_with_carry()
        cur.append(s)
        cur_len += len(s)
    if cur:
        chunks.append("".join(cur))
    return chunks

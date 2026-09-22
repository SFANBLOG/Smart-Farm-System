"""知识库模块：PDF/TXT 导入自动切片向量化、语义检索、reindex 重建、CRUD。"""
import os
import uuid
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from app.common.result import Result
from app.common.crud import dump_one, to_page
from app.models import KnowledgeDoc, KnowledgeChunk
from app.rag.vectorstore import hash_embedding, tokenize, chunk_text
from app.rag import retriever

router = APIRouter(prefix="/knowledge", tags=["知识库"])


def _extract_text(path: str, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception:
            return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


async def _index_doc(title: str, text: str, source: str, kind: str) -> KnowledgeDoc:
    chunks = chunk_text(text)
    doc = await KnowledgeDoc.create(title=title, source=source, kind=kind,
                                    size=len(text), chunk_count=len(chunks))
    for i, c in enumerate(chunks):
        await KnowledgeChunk.create(doc=doc, idx=i, content=c,
                                    embedding=hash_embedding(c), tokens=tokenize(c))
    return doc


@router.post("/upload", response_model=Result, summary="知识库-导入文档")
async def upload(file: UploadFile = File(...)):
    os.makedirs("uploads/kb", exist_ok=True)
    name = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join("uploads/kb", name)
    with open(path, "wb") as f:
        f.write(await file.read())
    kind = "pdf" if (file.filename or "").lower().endswith(".pdf") else "txt"
    text = _extract_text(path, file.filename or "")
    if not text.strip():
        return Result.fail("无法解析文本内容", 400)
    doc = await _index_doc(os.path.splitext(file.filename or "doc")[0], text, file.filename, kind)
    return Result.ok(dump_one(doc), f"已索引 {doc.chunk_count} 个切片")


class TextInput(BaseModel):
    title: str
    content: str


@router.post("/text", response_model=Result, summary="知识库-文本录入")
async def add_text(body: TextInput):
    doc = await _index_doc(body.title, body.content, "manual", "txt")
    return Result.ok(dump_one(doc), "录入成功")


@router.get("/search", response_model=Result, summary="知识库-语义检索")
async def search(q: str, top_k: int = 5):
    return Result.ok(await retriever.retrieve(q, top_k))


@router.post("/reindex", response_model=Result, summary="知识库-重建索引")
async def reindex():
    chunks = await KnowledgeChunk.all()
    for c in chunks:
        c.embedding = hash_embedding(c.content)
        c.tokens = tokenize(c.content)
        await c.save()
    return Result.ok({"reindexed": len(chunks)}, "索引已重建")


@router.get("/docs", response_model=Result, summary="知识库-文档分页")
async def docs(page: int = 1, size: int = 20):
    return Result.ok(await to_page(KnowledgeDoc, page, size, order="-id"))


@router.get("/{doc_id}/chunks", response_model=Result, summary="知识库-文档切片")
async def chunks(doc_id: int):
    rows = await KnowledgeChunk.filter(doc_id=doc_id).order_by("idx")
    return Result.ok([{"id": r.id, "idx": r.idx, "content": r.content} for r in rows])


@router.delete("/{doc_id}", response_model=Result, summary="知识库-删除文档")
async def delete_doc(doc_id: int):
    await KnowledgeChunk.filter(doc_id=doc_id).delete()
    await KnowledgeDoc.filter(id=doc_id).delete()
    return Result.ok({"id": doc_id})

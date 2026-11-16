from sqlalchemy import select, or_
from app.models import Memory, MemoryEmbedding, KnowledgeDocument, DocumentChunk
from app.providers.ollama import provider, ProviderError
from app.core.config import get_settings

async def index_memory(db, memory):
    db.query(MemoryEmbedding).filter_by(memory_id=memory.id).delete()
    try:
        vector = await provider().create_embedding(memory.title + '\n' + memory.content)
        db.add(MemoryEmbedding(memory_id=memory.id, model=get_settings().ollama_embedding_model, embedding=vector))
        db.commit()
        return True
    except ProviderError:
        db.commit()
        return False

async def search_memories(db, user_id, query, chat_only=False, semantic=False):
    statement = select(Memory).where(Memory.owner_id == user_id)
    if chat_only: statement = statement.where(Memory.use_in_chat.is_(True))
    if semantic and query and db.bind.dialect.name == 'postgresql':
        indexed = db.scalar(select(MemoryEmbedding.id).join(Memory).where(Memory.owner_id == user_id, MemoryEmbedding.model == get_settings().ollama_embedding_model, *([Memory.use_in_chat.is_(True)] if chat_only else [])).limit(1))
        if not indexed: semantic = False
    if semantic and query and db.bind.dialect.name == 'postgresql':
        try:
            vector = await provider().create_embedding(query)
            distance = MemoryEmbedding.embedding.cosine_distance(vector)
            return list(db.scalars(statement.join(MemoryEmbedding).where(MemoryEmbedding.model == get_settings().ollama_embedding_model, distance < 0.55).order_by(distance).limit(5))), 'semantic'
        except ProviderError: pass
    if query:
        statement = statement.where(or_(Memory.title.icontains(query, autoescape=True), Memory.content.icontains(query, autoescape=True)))
    return list(db.scalars(statement.order_by(Memory.created_at.desc()).limit(30))), 'text'

async def chunk_document(db, document):
    db.query(DocumentChunk).filter_by(document_id=document.id).delete()
    # Overlap preserves sentences spanning chunk boundaries. Text remains searchable offline.
    for start in range(0, min(len(document.content), 1000000), 1200):
        db.add(DocumentChunk(document_id=document.id, content=document.content[start:start + 1500]))
    db.commit()

async def index_document(db, document):
    chunks = list(db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document.id)))
    count = 0
    for chunk in chunks:
        chunk.embedding = await provider().create_embedding(chunk.content)
        chunk.embedding_model = get_settings().ollama_embedding_model
        count += 1
    db.commit()
    return count

async def search_documents(db, user_id, query, semantic=True):
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.owner_id == user_id)
    if query and semantic and db.bind.dialect.name == 'postgresql':
        try:
            vector = await provider().create_embedding(query)
            distance = DocumentChunk.embedding.cosine_distance(vector)
            hits = list(db.execute(select(DocumentChunk.document_id, DocumentChunk.content, distance.label('distance')).join(KnowledgeDocument).where(KnowledgeDocument.owner_id == user_id, DocumentChunk.embedding_model == get_settings().ollama_embedding_model, distance < 0.55).order_by(distance).limit(15)))
            ids = list(dict.fromkeys(hit.document_id for hit in hits))[:5]
            rows = {r.id: r for r in db.scalars(stmt.where(KnowledgeDocument.id.in_(ids)))}
            for hit in reversed(hits):
                if hit.document_id in rows: rows[hit.document_id]._search_excerpt = hit.content
            return [rows[i] for i in ids if i in rows], 'semantic'
        except ProviderError: pass
    if query: stmt = stmt.where(or_(KnowledgeDocument.title.icontains(query, autoescape=True), KnowledgeDocument.content.icontains(query, autoescape=True)))
    return list(db.scalars(stmt.order_by(KnowledgeDocument.created_at.desc()).limit(30))), 'text'

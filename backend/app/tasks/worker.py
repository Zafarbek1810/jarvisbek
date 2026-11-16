from celery import Celery
from app.core.config import get_settings

celery = Celery('jarvis', broker=get_settings().redis_url, backend=get_settings().redis_url)
celery.conf.update(task_serializer='json', accept_content=['json'], result_serializer='json', timezone='Asia/Samarkand', enable_utc=True)

@celery.task(name='jarvis.index_memory')
def index_memory_task(memory_id, owner_id):
    import asyncio
    from app.core.database import SessionLocal
    from app.models import Memory
    from app.core.security import owned
    from app.memory.service import index_memory
    with SessionLocal() as db:
        memory = owned(db, Memory, memory_id, owner_id)
        return asyncio.run(index_memory(db, memory))

@celery.task(name='jarvis.index_document')
def index_document_task(document_id, owner_id):
    import asyncio
    from app.core.database import SessionLocal
    from app.models import KnowledgeDocument
    from app.core.security import owned
    from app.memory.service import index_document
    with SessionLocal() as db:
        document = owned(db, KnowledgeDocument, document_id, owner_id)
        return asyncio.run(index_document(db, document))

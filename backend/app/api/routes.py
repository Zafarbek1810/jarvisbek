import io
import json
from datetime import datetime, timezone
from typing import Literal, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, Request, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pypdf import PdfReader
from app.core.database import get_db, SessionLocal
from app.core.security import current_user, hasher, DUMMY_PASSWORD_HASH, verify, issue_tokens, digest, owned, audit
from app.core.config import get_settings
from app.models import *
from app.schemas import *
from app.providers.ollama import provider, ProviderError
from app.providers import telegram, voice
from redis.exceptions import RedisError
from app.providers.voice import AzureVoice
from app.memory.service import index_memory, search_memories, chunk_document, search_documents
from app.agents.brain import respond, user_ai_settings
from app.agents.tools import REGISTRY, execute

router = APIRouter(prefix='/api/v1')

def serialize(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns if column.name not in ('password_hash', 'token_hash', 'owner_id')}

def tokens_response(db, user, response, mobile=False):
    result = issue_tokens(db, user)
    if not mobile:
        response.set_cookie('jarvis_refresh', result.pop('refresh_token'), httponly=True, secure=get_settings().cookie_secure, samesite='strict', path='/api/v1/auth', max_age=1209600)
    return result

@router.post('/auth/register', status_code=201)
def register(data: Register, response: Response, mobile: bool = False, db: Session = Depends(get_db)):
    user = User(email=data.email.lower(), name=data.name, password_hash=hasher.hash(data.password)); db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, 'Bu elektron pochta band.')
    audit(db, user.id, 'auth:register'); db.commit()
    return tokens_response(db, user, response, mobile)

@router.post('/auth/login')
def login(data: Credentials, response: Response, mobile: bool = False, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    # Equal-cost password verification for unknown identities.
    target = user.password_hash if user else DUMMY_PASSWORD_HASH
    valid = verify(data.password, target)
    if not user or not valid: raise HTTPException(401, 'Pochta yoki parol noto‘g‘ri.')
    return tokens_response(db, user, response, mobile)

@router.post('/auth/refresh')
def refresh(data: RefreshIn, request: Request, response: Response, mobile: bool = False, db: Session = Depends(get_db)):
    token = data.refresh_token if mobile else request.cookies.get('jarvis_refresh')
    if not token: raise HTTPException(401, 'Qayta kiring.')
    # Atomic update prevents a refresh token from being consumed concurrently twice.
    record = db.execute(update(RefreshToken).where(RefreshToken.token_hash == digest(token), RefreshToken.revoked.is_(False), RefreshToken.expires_at > datetime.now(timezone.utc)).values(revoked=True).returning(RefreshToken.owner_id)).first()
    if not record: db.rollback(); raise HTTPException(401, 'Sessiya muddati tugagan.')
    user = db.get(User, record[0])
    return tokens_response(db, user, response, mobile)

@router.post('/auth/logout')
def logout(data: RefreshIn, request: Request, response: Response, db: Session = Depends(get_db)):
    token = data.refresh_token or request.cookies.get('jarvis_refresh')
    if token:
        db.execute(update(RefreshToken).where(RefreshToken.token_hash == digest(token)).values(revoked=True)); db.commit()
    response.delete_cookie('jarvis_refresh', path='/api/v1/auth')
    return {'message': 'Hisobdan chiqildi.'}

@router.get('/users/me')
def me(user=Depends(current_user)): return {'id': user.id, 'name': user.name, 'email': user.email}

# Common CRUD uses explicit schemas and owner checks on every operation.
def add_crud(path, model, schema):
    def listing(q: str = '', limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0), sort: str = Query('newest', pattern='^(newest|oldest|title)$'), completed: Optional[bool] = None, category: str = '', user=Depends(current_user), db: Session = Depends(get_db)):
        stmt = select(model).where(model.owner_id == user.id)
        if q: stmt = stmt.where(model.title.icontains(q, autoescape=True))
        if category and hasattr(model, 'category'): stmt = stmt.where(model.category == category)
        if completed is not None and model == Task: stmt = stmt.where(Task.completed == completed)
        total = db.scalar(select(func.count()).select_from(stmt.subquery()))
        order = model.title if sort == 'title' else model.created_at.asc() if sort == 'oldest' else model.created_at.desc()
        return {'items': [serialize(r) for r in db.scalars(stmt.order_by(order).limit(limit).offset(offset))], 'total': total}
    async def creating(data, user=Depends(current_user), db: Session = Depends(get_db)):
        if model == Task and data.project_id: owned(db, Project, data.project_id, user.id)
        row = model(owner_id=user.id, **data.model_dump()); db.add(row); db.flush(); audit(db, user.id, path + ':create', row.id); db.commit()
        indexed = None
        if model == Memory: indexed = await index_memory(db, row)
        if model == KnowledgeDocument: await chunk_document(db, row)
        result = serialize(row)
        if indexed is not None: result['indexed'] = indexed
        return result
    creating.__annotations__['data'] = schema
    async def editing(item_id: str, data, user=Depends(current_user), db: Session = Depends(get_db)):
        row = owned(db, model, item_id, user.id)
        if model == Task and data.project_id: owned(db, Project, data.project_id, user.id)
        for key, value in data.model_dump().items(): setattr(row, key, value)
        audit(db, user.id, path + ':update', row.id); db.commit()
        if model == Memory: await index_memory(db, row)
        if model == KnowledgeDocument: await chunk_document(db, row)
        return serialize(row)
    editing.__annotations__['data'] = schema
    def deleting(item_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
        row = owned(db, model, item_id, user.id); audit(db, user.id, path + ':delete', row.id); db.delete(row); db.commit()
        return {'message': 'O‘chirildi.'}
    def reading(item_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
        return serialize(owned(db, model, item_id, user.id))
    for endpoint in (listing, creating, editing, deleting, reading): endpoint.__name__ = path + '_' + endpoint.__name__
    router.add_api_route('/' + path, listing, methods=['GET'])
    router.add_api_route('/' + path, creating, methods=['POST'], status_code=201)
    router.add_api_route('/' + path + '/{item_id}', editing, methods=['PUT'])
    router.add_api_route('/' + path + '/{item_id}', deleting, methods=['DELETE'])
    router.add_api_route('/' + path + '/{item_id}', reading, methods=['GET'])

@router.get('/memories/search')
async def memory_search(q: str = '', semantic: bool = True, user=Depends(current_user), db: Session = Depends(get_db)):
    rows, mode = await search_memories(db, user.id, q, semantic=semantic)
    return {'items': [serialize(r) for r in rows], 'total': len(rows), 'mode': mode}

@router.get('/memories/{item_id}/history')
def memory_history(item_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    owned(db, Memory, item_id, user.id)
    return {'items': [serialize(r) for r in db.scalars(select(AuditLog).where(AuditLog.owner_id == user.id, AuditLog.resource_id == item_id).order_by(AuditLog.created_at.desc()))]}

@router.get('/knowledge/search')
async def knowledge_search(q: str = '', semantic: bool = True, user=Depends(current_user), db: Session = Depends(get_db)):
    rows, mode = await search_documents(db, user.id, q, semantic)
    return {'items': [serialize(r) for r in rows], 'total': len(rows), 'mode': mode}

@router.post('/knowledge/{item_id}/index')
def knowledge_index(item_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    owned(db, KnowledgeDocument, item_id, user.id)
    from app.tasks.worker import index_document_task
    try: task = index_document_task.delay(item_id, user.id)
    except Exception: raise HTTPException(503, 'Fon xizmati ulanmagan. Redis va Celery worker’ni ishga tushiring.')
    audit(db, user.id, 'knowledge:index', item_id); db.commit()
    return {'job_id': task.id, 'message': 'Vektor yaratish navbatga qo‘yildi.'}

@router.post('/knowledge/upload', status_code=201)
async def upload(file: UploadFile = File(...), user=Depends(current_user), db: Session = Depends(get_db)):
    name = (file.filename or '').rsplit('/', 1)[-1].rsplit('\\', 1)[-1][:255]
    extension = name.rsplit('.', 1)[-1].lower()
    if extension not in ('txt', 'md', 'pdf'): raise HTTPException(415, 'Faqat TXT, MD va PDF fayllar qabul qilinadi.')
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024: raise HTTPException(413, 'Fayl 5 MB dan katta bo‘lmasin.')
    try:
        if extension == 'pdf':
            if not data.startswith(b'%PDF-'): raise ValueError()
            reader = PdfReader(io.BytesIO(data))
            if len(reader.pages) > 200: raise ValueError()
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        else:
            text = data.decode('utf-8')
            if '\x00' in text: raise ValueError()
        if not text.strip() or len(text) > 1000000: raise ValueError()
    except Exception: raise HTTPException(422, 'Fayldan matn olinmadi. Shifrlanmagan, matnli fayl tanlang.')
    row = KnowledgeDocument(owner_id=user.id, title=name[:200], content=text, filename=name, category='Hujjatlar'); db.add(row); db.flush(); audit(db, user.id, 'knowledge:upload', row.id); db.commit()
    await chunk_document(db, row)
    return serialize(row)

@router.post('/knowledge/{item_id}/summarize')
async def summarize(item_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    row = owned(db, KnowledgeDocument, item_id, user.id)
    try: result = await execute(db, user, 'summarize_documents', {'id': item_id}, [])
    except ProviderError as exc: raise HTTPException(503, str(exc))
    row.summary = json.loads(result); db.commit(); return serialize(row)

for path, model, schema in [('tasks', Task, TaskIn), ('memories', Memory, MemoryIn), ('projects', Project, ProjectIn), ('knowledge', KnowledgeDocument, KnowledgeIn), ('business', BusinessEntry, BusinessIn)]:
    add_crud(path, model, schema)

@router.get('/conversations')
def conversations(q: str = '', user=Depends(current_user), db: Session = Depends(get_db)):
    return {'items': [serialize(r) for r in db.scalars(select(Conversation).where(Conversation.owner_id == user.id, Conversation.title.icontains(q, autoescape=True)).order_by(Conversation.created_at.desc()).limit(100))]}

@router.get('/conversations/{item_id}/messages')
def messages(item_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    owned(db, Conversation, item_id, user.id)
    return {'items': [serialize(r) for r in db.scalars(select(Message).where(Message.conversation_id == item_id).order_by(Message.created_at, Message.id))]}

@router.delete('/conversations/{item_id}')
def delete_conversation(item_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned(db, Conversation, item_id, user.id)); audit(db, user.id, 'conversation:delete', item_id); db.commit(); return {'message': 'Suhbat o‘chirildi.'}

@router.post('/chat/stream')
def chat(data: ChatIn, request: Request, user=Depends(current_user), db: Session = Depends(get_db)):
    if any(name not in REGISTRY for name in data.allowed_tools): raise HTTPException(422, 'Noma’lum vosita.')
    if data.conversation_id: conversation = owned(db, Conversation, data.conversation_id, user.id)
    else:
        conversation = Conversation(owner_id=user.id, title=data.content[:100]); db.add(conversation); db.commit()
    if data.regenerate:
        if not data.conversation_id: raise HTTPException(422, 'Suhbatni tanlang.')
        last = db.scalar(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.desc(), Message.id.desc()).limit(1))
        last_user = db.scalar(select(Message).where(Message.conversation_id == conversation.id, Message.role == 'user').order_by(Message.created_at.desc(), Message.id.desc()).limit(1))
        if not last_user: raise HTTPException(422, 'Qayta javob olish uchun xabar yo‘q.')
        data.content = last_user.content
        if last and last.role == 'assistant': db.delete(last)
        db.commit()
    desktop_enabled = (
        not data.regenerate and get_settings().desktop_voice_commands
        and get_settings().environment == 'development'
        and request.client is not None and request.client.host in ('127.0.0.1', '::1')
        and request.headers.get('origin') in ('http://localhost:3010', 'http://127.0.0.1:3010')
    )
    user_id, conversation_id = user.id, conversation.id
    async def stream():
        # Generator owns its session; request dependency lifetimes never close it mid-stream.
        with SessionLocal() as session:
            person = session.get(User, user_id); conv = session.get(Conversation, conversation_id)
            yield json.dumps({'type': 'start', 'conversation_id': conversation_id}) + '\n'
            async for event in respond(session, person, conv, data.content, data.allowed_tools, data.regenerate, desktop_enabled, data.voice_turn):
                yield json.dumps(event, ensure_ascii=False) + '\n'
    return StreamingResponse(stream(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@router.get('/ai/status')
async def ai_status(user=Depends(current_user), db: Session = Depends(get_db)):
    result = await provider(user_ai_settings(db, user.id)).health_check()
    cfg = get_settings()
    result['settings'] = {'model': cfg.ollama_chat_model, 'temperature': cfg.ollama_temperature, 'context_length': cfg.ollama_context_length, 'think': cfg.ollama_think, **user_ai_settings(db, user.id)}
    result['commands'] = ['ollama serve', 'ollama pull ' + cfg.ollama_chat_model, 'ollama pull ' + cfg.ollama_fallback_model, 'ollama pull ' + cfg.ollama_embedding_model]
    return result

@router.put('/ai/settings')
async def ai_settings(data: AISettings, user=Depends(current_user), db: Session = Depends(get_db)):
    health = await provider().health_check()
    if data.model not in health.get('models', []): raise HTTPException(422, 'Faqat o‘rnatilgan modelni tanlash mumkin.')
    row = db.scalar(select(UserSettings).where(UserSettings.owner_id == user.id))
    if not row: row = UserSettings(owner_id=user.id, settings={}); db.add(row)
    row.settings = {**row.settings, 'ai': data.model_dump()}; audit(db, user.id, 'ai:settings'); db.commit()
    return {'message': 'AI sozlamalari saqlandi.'}

@router.get('/settings')
def settings(user=Depends(current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(UserSettings).where(UserSettings.owner_id == user.id)); return row.settings if row else {'theme': 'dark'}

@router.put('/settings')
def save_settings(data: PreferenceIn, user=Depends(current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(UserSettings).where(UserSettings.owner_id == user.id))
    if not row: row = UserSettings(owner_id=user.id, settings={}); db.add(row)
    row.settings = {**row.settings, **data.model_dump()}; db.commit(); return row.settings

@router.get('/dashboard')
def dashboard(user=Depends(current_user), db: Session = Depends(get_db)):
    counts = {name: db.scalar(select(func.count()).select_from(model).where(model.owner_id == user.id)) for name, model in [('memories', Memory), ('tasks', Task), ('projects', Project), ('knowledge', KnowledgeDocument)]}
    counts['completed'] = db.scalar(select(func.count()).select_from(Task).where(Task.owner_id == user.id, Task.completed.is_(True)))
    return {'counts': counts, 'tasks': [serialize(r) for r in db.scalars(select(Task).where(Task.owner_id == user.id, Task.completed.is_(False)).order_by(Task.created_at.desc()).limit(5))], 'projects': [serialize(r) for r in db.scalars(select(Project).where(Project.owner_id == user.id).limit(4))]}

@router.get('/integrations')
async def integrations(user=Depends(current_user)):
    items = [{'name': name, 'connected': False, 'message': 'Hali ulanmagan.'}
             for name in ['GitHub', 'Google Calendar', 'Elektron pochta', 'Notion']]
    try:
        state = await telegram.status(user.id)
    except RedisError:
        raise HTTPException(503, 'Telegram holatini o‘qib bo‘lmadi. Redis xizmatini tekshiring.')
    message = ('Telegram bot tokeni sozlanmagan.' if not state['configured']
               else 'Telegram bot jarayonini ishga tushiring.' if not state['worker_online']
               else 'Hisobingiz Telegram botga ulangan.' if state['connected']
               else 'Telegram’da Jarvis bilan matnli suhbat qiling.')
    items.insert(3, {'name': 'Telegram', 'message': message, **state})
    return {'items': items}


@router.post('/integrations/telegram/pair')
async def pair_telegram(user=Depends(current_user)):
    try:
        return await telegram.create_pairing(user.id)
    except (telegram.TelegramError, RedisError) as exc:
        raise HTTPException(503, 'Telegram ulash havolasi yaratilmadi. Bot tokeni va xizmatlarni tekshiring.') from exc


@router.delete('/integrations/telegram')
async def disconnect_telegram(user=Depends(current_user)):
    try:
        await telegram.disconnect(user.id)
    except RedisError as exc:
        raise HTTPException(503, 'Telegram ulanishini uzib bo‘lmadi.') from exc
    return {'connected': False}


@router.get('/voice/status')
async def voice_status(user=Depends(current_user)):
    return await voice.voice_status()

@router.post('/voice/transcribe')
async def transcribe(file: UploadFile = File(...), model: Optional[str] = Form(None), user=Depends(current_user), db: Session = Depends(get_db)):
    if not get_settings().voice_stt_url:
        raise HTTPException(503, 'Mahalliy nutqni tanish xizmati sozlanmagan. Matnli suhbatdan foydalaning.')
    data = await file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024: raise HTTPException(413, 'Ovoz fayli 10 MB dan oshmasin.')
    mime = (file.content_type or '').split(';')[0].strip().lower()
    if mime not in ['audio/wav', 'audio/x-wav', 'audio/webm', 'audio/mp4', 'audio/m4a', 'audio/x-m4a', 'audio/ogg']:
        raise HTTPException(415, 'Ovoz formati qo‘llab-quvvatlanmaydi.')
    if not data: raise HTTPException(422, 'Ovoz yozuvi bo‘sh. Qayta yozib ko‘ring.')
    try:
        text = await voice.transcribe_audio(data, model) if model else await voice.transcribe_audio(data)
    except voice.VoiceError as exc:
        raise HTTPException(503, str(exc)) from exc
    audit(db, user.id, 'voice:transcribe'); db.commit()
    return {'text': text, 'warning': 'O‘zbekcha tanish sifati talaffuzga bog‘liq.'}


class SpeechIn(Strict):
    text: str = Field(min_length=1, max_length=3000)
    voice: AzureVoice = 'uz-UZ-SardorNeural'
    local_voice: Optional[Literal['speecht5', 'espeak']] = None

@router.post('/voice/speak')
async def speak(data: SpeechIn, user=Depends(current_user)):
    cfg = get_settings()
    if cfg.voice_tts_engine == 'edge' and not cfg.voice_tts_url:
        try:
            return Response(await voice.synthesize_edge(data.text, data.voice), media_type='audio/mpeg')
        except voice.VoiceError as exc:
            raise HTTPException(503, str(exc)) from exc
    if cfg.voice_tts_engine == 'azure' and not cfg.voice_tts_url:
        try:
            return Response(await voice.synthesize_azure(data.text, data.voice), media_type='audio/wav')
        except voice.VoiceError as exc:
            raise HTTPException(503, str(exc)) from exc
    if ((cfg.voice_tts_engine == 'espeak' and not cfg.voice_tts_url)
            or (cfg.voice_local_only and cfg.voice_tts_engine == 'speecht5' and data.local_voice == 'espeak')):
        try:
            return Response(await voice.synthesize_local(data.text), media_type='audio/wav')
        except voice.VoiceError as exc:
            raise HTTPException(503, str(exc)) from exc
    if not cfg.voice_tts_url: raise HTTPException(503, 'Mahalliy ovoz yaratish xizmati sozlanmagan.')
    try:
        async with httpx.AsyncClient(timeout=120, trust_env=not cfg.voice_local_only) as client:
            response = await client.post(cfg.voice_tts_url.rstrip('/') + '/synthesize', json={'text': data.text, 'language': 'uz'}); response.raise_for_status()
            if len(response.content) > 20 * 1024 * 1024: raise ValueError()
            return Response(response.content, media_type='audio/wav')
    except (httpx.HTTPError, ValueError): raise HTTPException(503, 'Ovoz yaratilmadi. Mahalliy adapter sozlamalarini tekshiring.')

class ProjectNoteIn(Strict):
    content: str = Field(min_length=1, max_length=30000)

@router.get('/projects/{item_id}/notes')
def project_notes(item_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    owned(db, Project, item_id, user.id)
    return {'items': [serialize(row) for row in db.scalars(select(ProjectNote).where(ProjectNote.owner_id == user.id, ProjectNote.project_id == item_id).order_by(ProjectNote.created_at.desc()))]}

@router.post('/projects/{item_id}/notes', status_code=201)
def create_project_note(item_id: str, data: ProjectNoteIn, user=Depends(current_user), db: Session = Depends(get_db)):
    owned(db, Project, item_id, user.id)
    row = ProjectNote(owner_id=user.id, project_id=item_id, content=data.content); db.add(row); db.flush(); audit(db, user.id, 'project:note', row.id); db.commit(); return serialize(row)

@router.delete('/projects/{item_id}/notes/{note_id}')
def delete_project_note(item_id: str, note_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    owned(db, Project, item_id, user.id)
    row = owned(db, ProjectNote, note_id, user.id)
    if row.project_id != item_id: raise HTTPException(404, 'Qayd topilmadi.')
    db.delete(row); audit(db, user.id, 'project:note:delete', note_id); db.commit(); return {'message': 'Qayd o‘chirildi.'}

class CodeIn(Strict):
    text: str = Field(min_length=1, max_length=30000)

@router.post('/projects/analyze-code')
async def analyze_code(data: CodeIn, user=Depends(current_user), db: Session = Depends(get_db)):
    try: result = await execute(db, user, 'analyze_code', data.model_dump(), [])
    except ProviderError as exc: raise HTTPException(503, str(exc))
    return {'analysis': json.loads(result), 'message': 'Kod bajarilmadi; matn sifatida tahlil qilindi.'}

@router.get('/business/report/summary')
async def business_report(currency: str = Query('UZS', pattern='^(UZS|USD)$'), ai: bool = False, user=Depends(current_user), db: Session = Depends(get_db)):
    report = json.loads(await execute(db, user, 'generate_reports', {'currency': currency}, []))
    if ai:
        from app.agents.tools import collect_text
        try:
            report['summary'] = await collect_text([{'role': 'system', 'content': 'Haqiqiy moliyaviy yozuvlardan berilgan hisobotni o‘zbekcha tushuntiring. Boshqa miqdorlarni to‘qimang. Taxmin bo‘lsa aniq belgilang.'}, {'role': 'user', 'content': json.dumps(report, ensure_ascii=False)}], user_ai_settings(db, user.id))
        except ProviderError as exc: raise HTTPException(503, str(exc))
    return report

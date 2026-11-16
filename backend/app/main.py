import json
import logging
import time
from collections import defaultdict, deque
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from sqlalchemy import text
from app.core.config import get_settings
from app.core.database import engine
from app.api.routes import router

cfg = get_settings()
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('jarvis')
app = FastAPI(title='JARVIS API', version='1.0.0', description='O‘zbekcha shaxsiy yordamchi')
app.add_middleware(CORSMiddleware, allow_origins=cfg.origins, allow_credentials=True, allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])

# Bounded local limiter for one process; Redis provides shared production counters.
local_windows = defaultdict(deque)

@app.middleware('http')
async def protection(request: Request, call_next):
    start = time.monotonic()
    origin = request.headers.get('origin')
    if request.method in ('POST', 'PUT', 'DELETE') and origin and origin not in cfg.origins:
        return JSONResponse({'error': {'message': 'Manba ruxsat etilmagan.'}}, status_code=403)
    try: content_length = int(request.headers.get('content-length', '0') or 0)
    except ValueError: return JSONResponse({'error': {'message': 'So‘rov hajmi noto‘g‘ri.'}}, status_code=400)
    if content_length > 11 * 1024 * 1024:
        return JSONResponse({'error': {'message': 'So‘rov hajmi juda katta.'}}, status_code=413)
    key = (request.client.host if request.client else 'local') + (':auth' if '/auth/' in request.url.path else ':api')
    limit = 20 if ':auth' in key else 180
    try:
        from redis.asyncio import Redis
        redis = Redis.from_url(cfg.redis_url, socket_connect_timeout=0.3, socket_timeout=0.3)
        try:
            bucket = 'rate:' + key + ':' + str(int(time.time() // 60))
            count = await redis.incr(bucket)
            if count == 1: await redis.expire(bucket, 65)
        finally: await redis.aclose()
    except Exception:
        if cfg.environment == 'production':
            return JSONResponse({'error': {'message': 'Himoya xizmati vaqtincha ishlamayapti.'}}, status_code=503)
        window = local_windows[key]
        while window and window[0] < start - 60: window.popleft()
        window.append(start); count = len(window)
        if len(local_windows) > 10000: local_windows.clear()
    if count > limit: return JSONResponse({'error': {'message': 'So‘rovlar ko‘p. Bir daqiqadan so‘ng qayta urinib ko‘ring.'}}, status_code=429, headers={'Retry-After': '60'})
    try: response = await call_next(request)
    except Exception:
        logger.exception(json.dumps({'event': 'request_error', 'path': request.url.path}))
        return JSONResponse({'error': {'message': 'Ichki xatolik. Keyinroq qayta urinib ko‘ring.'}}, status_code=500)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    logger.info(json.dumps({'event': 'request', 'method': request.method, 'path': request.url.path, 'status': response.status_code, 'duration_ms': round((time.monotonic()-start)*1000)}))
    return response

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse({'error': {'message': 'Kiritilgan ma’lumot noto‘g‘ri. Maydonlarni tekshiring.', 'fields': ['.'.join(str(x) for x in e['loc']) for e in exc.errors()]}}, status_code=422)

@app.exception_handler(HTTPException)
async def http_error(request, exc):
    message = {'Not Found': 'Yo‘l topilmadi.', 'Method Not Allowed': 'Bu usulga ruxsat berilmagan.'}.get(str(exc.detail), exc.detail)
    return JSONResponse({'error': {'message': message}}, status_code=exc.status_code)

@app.get('/health')
def health(): return {'status': 'ok', 'service': 'JARVIS'}

@app.get('/ready')
def ready():
    try:
        with engine.connect() as conn: conn.execute(text('SELECT 1'))
        import redis
        redis.Redis.from_url(cfg.redis_url, socket_connect_timeout=1).ping()
        return {'database': True, 'redis': True}
    except Exception: return JSONResponse({'database_or_redis': False, 'message': 'Ma’lumotlar xizmatlarini tekshiring.'}, status_code=503)

app.include_router(router)

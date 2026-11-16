"""Telegram private-chat pairing and long polling."""
import asyncio
import json
import re
import secrets
from urllib.request import Request, urlopen

from redis.asyncio import Redis

from app.core.config import get_settings
from app.providers.ollama import ProviderError, provider


class TelegramError(Exception):
    pass


def _request(method, payload):
    token = get_settings().telegram_bot_token
    if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+', token):
        raise TelegramError('Telegram bot tokeni sozlanmagan yoki noto‘g‘ri.')
    try:
        request = Request(
            f'https://api.telegram.org/bot{token}/{method}',
            data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'},
        )
        with urlopen(request, timeout=35) as response:
            result = json.load(response)
        if result.get('ok'):
            return result['result']
    except (OSError, ValueError, KeyError):
        pass
    raise TelegramError('Telegram Bot API bilan aloqa bo‘lmadi.')


async def api(method, **payload):
    return await asyncio.to_thread(_request, method, payload)


def redis_client():
    return Redis.from_url(get_settings().redis_url, decode_responses=True, socket_connect_timeout=3)


def _key(suffix):
    bot_id = get_settings().telegram_bot_token.partition(':')[0]
    return f'jarvis:telegram:{bot_id}:{suffix}'


async def status(user_id):
    if not get_settings().telegram_bot_token:
        return {'configured': False, 'connected': False, 'worker_online': False}
    async with redis_client() as redis:
        connected, online = await redis.mget(_key(f'user:{user_id}'), _key('online'))
    return {'configured': True, 'connected': bool(connected), 'worker_online': bool(online)}


async def create_pairing(user_id):
    bot = await api('getMe')
    username = bot.get('username', '')
    if not re.fullmatch(r'[A-Za-z0-9_]+', username):
        raise TelegramError('Telegram bot nomi topilmadi.')
    code = secrets.token_urlsafe(24)
    async with redis_client() as redis:
        await redis.set(_key(f'pending:{user_id}'), code, ex=600)
        await redis.set(_key(f'code:{code}'), user_id, ex=600)
    return {'url': f'https://t.me/{username}?start={code}'}


async def disconnect(user_id):
    async with redis_client() as redis:
        await redis.eval("""
            local chat = redis.call('GET', KEYS[1])
            if chat then redis.call('DEL', KEYS[3] .. chat) end
            redis.call('DEL', KEYS[1], KEYS[2])
            """, 3, _key(f'user:{user_id}'), _key(f'pending:{user_id}'), _key('chat:'))


async def _pair(redis, code, chat):
    return await redis.eval("""
        local user = redis.call('GET', KEYS[1])
        if not user then return 0 end
        local pending = KEYS[2] .. user
        if redis.call('GET', pending) ~= ARGV[1] then return 0 end
        local owner = redis.call('GET', KEYS[4] .. ARGV[2])
        if owner and owner ~= user then return 0 end
        local user_key = KEYS[3] .. user
        local old_chat = redis.call('GET', user_key)
        if old_chat then redis.call('DEL', KEYS[4] .. old_chat) end
        redis.call('SET', user_key, ARGV[2])
        redis.call('SET', KEYS[4] .. ARGV[2], user)
        redis.call('DEL', KEYS[1], pending)
        return 1
        """, 4, _key(f'code:{code}'), _key('pending:'), _key('user:'), _key('chat:'), code, str(chat))


async def telegram_reply(text):
    model = provider({'model': 'qwen3:8b', 'think': False, 'temperature': 0.3})
    messages = [
        {'role': 'system', 'content': (
            'Sen Jarvis, Telegramdagi yordamchisan. O‘zbek lotin yozuvida tabiiy, sodda va aniq javob ber. '
            'Odatda 1–3 qisqa jumla yetarli. Savolga bevosita javob ber, uni takrorlama. '
            'Oddiy salomga qisqa salom bilan javob ber.'
        )},
        {'role': 'user', 'content': text[:4000]},
    ]
    parts = []
    async for part in model.generate_response(messages):
        parts.append(part.get('content', ''))
    reply = ''.join(parts).strip()
    if len(reply) > 700:
        reply = reply[:700].rsplit(' ', 1)[0] + '…'
    return reply or 'Jarvis javob qaytarmadi.'


async def handle_message(redis, message):
    chat = message.get('chat', {})
    text = message.get('text')
    if chat.get('type') != 'private' or not isinstance(text, str):
        return
    chat_id = chat['id']
    command, _, code = text.partition(' ')
    if command == '/start':
        paired = bool(re.fullmatch(r'[A-Za-z0-9_-]{32}', code)) and await _pair(redis, code, chat_id)
        reply = ('Jarvis hisobingiz ulandi. Savolingizni yozing.' if paired
                 else 'Jarvis → Integratsiyalar bo‘limidan yangi ulash havolasini oching.')
    elif await redis.get(_key(f'chat:{chat_id}')):
        try:
            reply = await telegram_reply(text)
        except ProviderError:
            reply = 'Mahalliy AI hozir javob bermadi.'
    else:
        return
    await api('sendMessage', chat_id=chat_id, text=reply[:2000])


async def run():
    await api('getMe')
    print('Jarvis Telegram bot ishga tushdi.', flush=True)
    async with redis_client() as redis:
        offset = None
        while True:
            try:
                updates = await api('getUpdates', offset=offset, timeout=20, allowed_updates=['message'])
                await redis.set(_key('online'), '1', ex=45)
                for update in updates:
                    offset = update['update_id'] + 1
                    await handle_message(redis, update.get('message', {}))
            except TelegramError as exc:
                print(str(exc), flush=True)
                await asyncio.sleep(5)


if __name__ == '__main__':
    try:
        asyncio.run(run())
    except TelegramError as exc:
        raise SystemExit(str(exc)) from None

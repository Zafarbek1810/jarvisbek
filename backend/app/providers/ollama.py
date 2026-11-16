import json
import shutil
from abc import ABC, abstractmethod
import httpx
from app.core.config import get_settings

class ProviderError(Exception): pass

class AIProvider(ABC):
    @abstractmethod
    async def generate_response(self, messages, tools=None): pass
    @abstractmethod
    async def create_embedding(self, text): pass
    @abstractmethod
    async def health_check(self): pass

class MockAIProvider(AIProvider):
    async def generate_response(self, messages, tools=None):
        yield {'content': '[SINOV JAVOBI] Bu simulyatsiya. Haqiqiy AI modeli ulanmagan. Sizning xabaringiz: ' + next((m['content'] for m in reversed(messages) if m['role'] == 'user'), '')}
    async def create_embedding(self, text):
        raise ProviderError('Sinov rejimida semantik qidiruv o‘chirilgan.')
    async def health_check(self):
        return {'provider': 'mock', 'connected': True, 'models': [], 'embedding_ready': False, 'message': 'Sinov rejimi: javoblar simulyatsiya qilinadi.'}

class OllamaProvider(AIProvider):
    def __init__(self, model=None, temperature=None, context_length=None, transport=None, think=None):
        self.cfg = get_settings()
        self.model = model or self.cfg.ollama_chat_model
        self.temperature = temperature if temperature is not None else self.cfg.ollama_temperature
        self.context_length = context_length or self.cfg.ollama_context_length
        self.transport = transport
        self.think = self.cfg.ollama_think if think is None else think
    def client(self, timeout=180):
        return httpx.AsyncClient(base_url=self.cfg.ollama_base_url, timeout=timeout, transport=self.transport, trust_env=not self.cfg.voice_local_only)
    async def installed_models(self, client):
        response = await client.get('/api/tags')
        response.raise_for_status()
        models = response.json().get('models', [])
        if self.cfg.voice_local_only:
            models = [
                model for model in models
                if not model.get('remote_host') and not model.get('remote_model')
                and not model['name'].endswith((':cloud', '-cloud'))
            ]
        return [model['name'] for model in models]

    async def require_local_model(self, client, name):
        if not self.cfg.voice_local_only:
            return
        installed = await self.installed_models(client)
        if name not in installed and f'{name}:latest' not in installed:
            raise ProviderError('Oflayn rejim uchun Ollama’da mahalliy model o‘rnatilgan bo‘lishi kerak.')

    async def health_check(self):
        try:
            async with self.client(5) as client:
                version = await client.get('/api/version'); version.raise_for_status()
                models = await self.installed_models(client)
                return {'provider': 'ollama', 'cli_installed': shutil.which('ollama') is not None, 'connected': True, 'version': version.json().get('version'), 'models': models, 'model': self.model, 'model_ready': self.model in models, 'embedding_ready': any(m.split(':')[0] == self.cfg.ollama_embedding_model.split(':')[0] for m in models), 'message': 'Ollama ulangan.' if self.model in models else 'Asosiy model topilmadi. O‘rnatish buyrug‘ini bajaring.'}
        except (httpx.HTTPError, ValueError, KeyError):
            return {'provider': 'ollama', 'cli_installed': shutil.which('ollama') is not None, 'connected': False, 'models': [], 'model': self.model, 'model_ready': False, 'embedding_ready': False, 'message': 'Ollama bilan aloqa yo‘q. ollama serve buyrug‘ini ishga tushiring.'}
    async def generate_response(self, messages, tools=None):
        payload = {'model': self.model, 'messages': messages, 'stream': self.cfg.ollama_stream, 'options': {'temperature': self.temperature, 'num_ctx': self.context_length}}
        payload['keep_alive'] = self.cfg.ollama_keep_alive
        # Qwen3 exposes a boolean thinking control; preserve other models’ defaults.
        if self.model.split(':')[0] == 'qwen3': payload['think'] = self.think
        if tools: payload['tools'] = tools
        try:
            async with self.client() as client:
                await self.require_local_model(client, self.model)
                async with client.stream('POST', '/api/chat', json=payload) as response:
                    if response.status_code >= 400:
                        await response.aread()
                        raise ProviderError('Modelni yuklab bo‘lmadi. Model mavjudligini va bo‘sh tezkor xotirani tekshiring.')
                    async for line in response.aiter_lines():
                        if not line: continue
                        data = json.loads(line)
                        if data.get('error'): raise ProviderError('Ollama xatosi. Model va tezkor xotirani tekshiring.')
                        yield data.get('message', {})
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError('Ollama javob bermadi. Xizmatni va modelni tekshiring.') from exc
    async def create_embedding(self, text):
        try:
            async with self.client(60) as client:
                await self.require_local_model(client, self.cfg.ollama_embedding_model)
                response = await client.post('/api/embed', json={'model': self.cfg.ollama_embedding_model, 'input': text})
                response.raise_for_status()
                vector = response.json()['embeddings'][0]
                if len(vector) != 768: raise ProviderError('Embedding o‘lchami 768 bo‘lishi kerak.')
                return vector
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            raise ProviderError('Xotira vektori yaratilmadi. nomic-embed-text modelini tekshiring.') from exc

def provider(settings=None):
    cfg = get_settings()
    if cfg.ai_provider == 'mock': return MockAIProvider()
    if cfg.ai_provider != 'ollama': raise ProviderError('AI provayderi qo‘llab-quvvatlanmaydi.')
    settings = settings or {}
    return OllamaProvider(settings.get('model'), settings.get('temperature'), settings.get('context_length'), think=settings.get('think'))

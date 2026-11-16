from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / '.env', extra='ignore')
    database_url: str = 'postgresql+psycopg://jarvis:jarvis@localhost:5432/jarvis'
    redis_url: str = 'redis://localhost:6379/0'
    jwt_secret: str = Field(min_length=32)
    environment: Literal['development', 'test', 'production'] = 'development'
    cors_origins: str = 'http://localhost:3010'
    ai_provider: Literal['ollama', 'mock'] = 'ollama'
    ollama_base_url: str = 'http://localhost:11434'
    ollama_chat_model: str = 'qwen3:8b'
    ollama_fallback_model: str = 'qwen3:4b'
    ollama_embedding_model: str = 'nomic-embed-text'
    ollama_context_length: int = Field(default=4096, ge=1024, le=32768)
    ollama_temperature: float = Field(default=0.6, ge=0, le=2)
    ollama_stream: bool = True
    ollama_think: bool = False
    ollama_keep_alive: str = '15m'
    telegram_bot_token: str = Field(default='', repr=False)
    desktop_voice_commands: bool = False
    voice_stt_url: str = ''
    voice_local_only: bool = False
    voice_allow_edge_tts: bool = False
    voice_stt_model: Literal['small', 'tiny', 'kotib'] = 'small'
    voice_stt_device: Literal['auto', 'cpu'] = 'auto'
    voice_tts_speed: int = Field(default=155, ge=100, le=220)
    voice_tts_url: str = ''
    voice_tts_engine: Literal['disabled', 'espeak', 'azure', 'edge', 'speecht5'] = 'disabled'
    azure_speech_key: str = Field(default='', repr=False)
    azure_speech_region: str = Field(default='', pattern=r'^[a-z0-9]*$')
    cookie_secure: bool = False
    @model_validator(mode='after')
    def production_security(self):
        if self.voice_local_only:
            edge_allowed = self.voice_tts_engine == 'edge' and self.voice_allow_edge_tts
            if self.voice_tts_engine not in ('espeak', 'speecht5', 'disabled') and not edge_allowed:
                raise ValueError('Mahalliy ovoz rejimida VOICE_TTS_ENGINE mahalliy sintezator bo‘lishi kerak.')
            if bool(self.voice_tts_url) != (self.voice_tts_engine == 'speecht5'):
                raise ValueError('VOICE_TTS_URL faqat mahalliy SpeechT5 adapteri uchun sozlanadi.')
            for address in (self.voice_stt_url, self.voice_tts_url, self.ollama_base_url):
                if not address:
                    continue
                url = urlsplit(address)
                if url.scheme not in ('http', 'https') or url.hostname not in ('localhost', '127.0.0.1', '::1'):
                    raise ValueError('Mahalliy ovoz rejimi loopback xizmatlarini talab qiladi.')
        if self.environment == 'production':
            if not self.cookie_secure: raise ValueError('Production uchun COOKIE_SECURE=true talab qilinadi.')
            if self.jwt_secret.startswith('replace-'): raise ValueError('Tasodifiy JWT_SECRET yarating.')
            if any(not origin.startswith('https://') for origin in self.origins): raise ValueError('Production CORS manbalari HTTPS bo‘lishi kerak.')
        return self
    @property
    def origins(self):
        return self.cors_origins.split(',')

@lru_cache
def get_settings():
    return Settings()

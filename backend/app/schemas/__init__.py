from typing import Literal, Optional
from datetime import date
from pydantic import BaseModel, Field, field_validator, ConfigDict

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Credentials(Strict):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=10, max_length=128)

class Register(Credentials):
    name: str = Field(min_length=1, max_length=100)

class TaskIn(Strict):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=20000)
    completed: bool = False
    priority: Literal['past', 'o‘rta', 'yuqori'] = 'o‘rta'
    due_date: str = ''
    category: str = Field(default='Shaxsiy', max_length=100)
    project_id: Optional[str] = None
    @field_validator('due_date')
    @classmethod
    def valid_date(cls, value):
        if value: date.fromisoformat(value)
        return value

class MemoryIn(Strict):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=40000)
    category: str = Field(default='Uzoq muddatli xotiralar', max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=30)
    use_in_chat: bool = True

class ProjectIn(Strict):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=20000)
    technologies: list[str] = Field(default_factory=list, max_length=40)
    repository_url: str = Field(default='', max_length=500, pattern=r'^(https://[^\s]+)?$')
    status: Literal['faol', 'yakunlangan', 'kutilmoqda'] = 'faol'

class KnowledgeIn(Strict):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=1000000)
    category: str = Field(default='Qaydlar', max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=30)
    source_url: str = Field(default='', max_length=1000, pattern=r'^(https?://[^\s]+)?$')

class BusinessIn(Strict):
    title: str = Field(min_length=1, max_length=200)
    kind: Literal['daromad', 'xarajat', 'g‘oya', 'kpi']
    amount: float = Field(default=0, ge=0, le=999999999999, allow_inf_nan=False)
    currency: Literal['UZS', 'USD'] = 'UZS'
    date: str
    note: str = Field(default='', max_length=20000)
    @field_validator('date')
    @classmethod
    def valid_date(cls, value):
        date.fromisoformat(value)
        return value

class ChatIn(Strict):
    voice_turn: bool = False
    regenerate: bool = False
    conversation_id: Optional[str] = None
    content: str = Field(min_length=1, max_length=12000)
    allowed_tools: list[str] = Field(default_factory=list, max_length=10)

class AISettings(Strict):
    think: bool = False
    model: str = Field(min_length=1, max_length=100)
    temperature: float = Field(default=0.6, ge=0, le=2)
    context_length: int = Field(default=4096, ge=1024, le=32768)
    system_prompt: str = Field(default='', max_length=12000)

class PreferenceIn(Strict):
    theme: Literal['dark', 'light'] = 'dark'

class RefreshIn(Strict):
    refresh_token: Optional[str] = Field(default=None, max_length=200)

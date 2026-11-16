import os
os.environ['JWT_SECRET'] = 'test-secret-only-' * 4
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['AI_PROVIDER'] = 'mock'
os.environ['OLLAMA_CHAT_MODEL'] = 'qwen3:8b'
os.environ['OLLAMA_FALLBACK_MODEL'] = 'qwen3:4b'
os.environ['VOICE_LOCAL_ONLY'] = 'false'
os.environ['REDIS_URL'] = 'redis://127.0.0.1:1/0'
os.environ['VOICE_STT_URL'] = ''
os.environ['VOICE_TTS_URL'] = ''
os.environ['VOICE_TTS_ENGINE'] = 'disabled'
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.core.database import Base, get_db
from app.main import app, local_windows
import app.api.routes as routes

@pytest.fixture
def client(monkeypatch):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    @event.listens_for(engine,'connect')
    def foreign_keys(connection, _): connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory=sessionmaker(engine,expire_on_commit=False)
    def override():
        with factory() as db: yield db
    app.dependency_overrides[get_db]=override
    monkeypatch.setattr(routes,'SessionLocal',factory)
    local_windows.clear()
    with TestClient(app) as test: yield test
    app.dependency_overrides.clear();Base.metadata.drop_all(engine);engine.dispose()

def register(client,email='ali@example.uz'):
    response=client.post('/api/v1/auth/register?mobile=true',json={'name':'Ali','email':email,'password':'secure-password-123'})
    assert response.status_code==201,response.text
    return response.json()

@pytest.fixture
def auth(client):
    data=register(client)
    return {'Authorization':'Bearer '+data['access_token']}

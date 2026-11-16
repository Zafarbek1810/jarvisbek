import json
import httpx
import pytest
from app.providers.ollama import OllamaProvider, MockAIProvider, ProviderError
from app.agents.tools import execute
from app.models import User
from app.core.database import get_db
from app.main import app

@pytest.mark.asyncio
async def test_provider_native_api():
    requests=[]
    def handler(request):
        requests.append(request)
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':'qwen3:8b'},{'name':'nomic-embed-text:latest'}]})
        if request.url.path=='/api/version':return httpx.Response(200,json={'version':'test'})
        if request.url.path=='/api/embed':return httpx.Response(200,json={'embeddings':[[0.1]*768]})
        return httpx.Response(200,text=json.dumps({'message':{'content':'Salom'}})+'\n'+json.dumps({'message':{'content':' dunyo'},'done':True})+'\n')
    provider=OllamaProvider(transport=httpx.MockTransport(handler))
    status=await provider.health_check();assert status['connected'] and status['embedding_ready']
    chunks=[part async for part in provider.generate_response([{'role':'user','content':'Salom'}])]
    assert ''.join(p['content'] for p in chunks)=='Salom dunyo'
    assert len(await provider.create_embedding('test'))==768
    assert json.loads(requests[-2].content)['options']['num_ctx']==4096

@pytest.mark.asyncio
async def test_provider_failure_and_missing_models():
    def handler(request):return httpx.Response(500,json={'error':'out of memory'})
    provider=OllamaProvider(transport=httpx.MockTransport(handler))
    assert not (await provider.health_check())['connected']
    with pytest.raises(ProviderError):
        async for _ in provider.generate_response([]): pass
    with pytest.raises(ProviderError):await provider.create_embedding('test')
    mock=MockAIProvider()
    chunks=[p async for p in mock.generate_response([])]
    assert '[SINOV JAVOBI]' in chunks[0]['content']
    with pytest.raises(ProviderError):await mock.create_embedding('text')

@pytest.mark.asyncio
async def test_tool_permission_schema_and_no_shell(client,auth):
    from conftest import register
    response=client.get('/api/v1/users/me',headers=auth).json()
    generator=app.dependency_overrides[get_db]()
    db=next(generator);user=db.get(User,response['id'])
    try:
        with pytest.raises(PermissionError):await execute(db,user,'create_task',{'title':'No'},[])
        with pytest.raises(ValueError):await execute(db,user,'shell',{'command':'rm -rf /'},['shell'])
        with pytest.raises(ValueError):await execute(db,user,'create_task',{'title':'','owner_id':'bad'},['create_task'])
        result=await execute(db,user,'create_task',{'title':'Ruxsatli vazifa'},['create_task'])
        assert 'Saqlandi' in result
        report=json.loads(await execute(db,user,'generate_reports',{'currency':'UZS'},[]));assert report['balance']==0
    finally:generator.close()

@pytest.mark.asyncio
async def test_embedding_dimension_and_missing_models():
    def handler(request):
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[]})
        if request.url.path=='/api/version':return httpx.Response(200,json={'version':'test'})
        return httpx.Response(200,json={'embeddings':[[0.1,0.2]]})
    provider=OllamaProvider(transport=httpx.MockTransport(handler))
    status=await provider.health_check();assert status['connected'] and not status['model_ready'] and not status['embedding_ready']
    with pytest.raises(ProviderError):await provider.create_embedding('test')

def test_primary_model_falls_back_only_to_installed_model(client,auth,monkeypatch):
    import app.agents.brain as brain
    requested=[]
    def handler(request):
        if request.url.path=='/api/version':return httpx.Response(200,json={'version':'test'})
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':'qwen3:4b'}]})
        requested.append(json.loads(request.content)['model'])
        return httpx.Response(200,text=json.dumps({'message':{'content':'O‘zbekcha javob'},'done':True})+'\n')
    monkeypatch.setattr(brain,'provider',lambda settings:OllamaProvider(transport=httpx.MockTransport(handler)))
    response=client.post('/api/v1/chat/stream',headers=auth,json={'content':'Salom'})
    assert requested==['qwen3:4b'] and 'Yengil zaxira model' in response.text and '"type": "done"' in response.text

def test_production_configuration_rejects_insecure_defaults():
    from app.core.config import Settings
    with pytest.raises(ValueError):Settings(_env_file=None,jwt_secret='x'*48,environment='production',cookie_secure=False)
    with pytest.raises(ValueError):Settings(_env_file=None,jwt_secret='x'*48,environment='production',cookie_secure=True,cors_origins='http://localhost:3010')

@pytest.mark.asyncio
@pytest.mark.parametrize('model,think,expected',[('qwen3:8b',None,False),('qwen3:4b',True,True),('different-model:latest',False,None)])
async def test_explicit_thinking_control_and_keep_alive(model,think,expected):
    payloads=[]
    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200,text=json.dumps({'message':{'content':'4.'},'done':True})+'\n')
    ai=OllamaProvider(model=model,think=think,transport=httpx.MockTransport(handler))
    result=[part async for part in ai.generate_response([{'role':'user','content':'2+2'}])]
    assert result[0]['content']=='4.'
    assert payloads[0]['keep_alive']=='15m'
    if expected is None:assert 'think' not in payloads[0]
    else:assert payloads[0]['think'] is expected

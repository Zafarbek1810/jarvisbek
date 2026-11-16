from conftest import register

def test_auth_rotation_and_logout(client):
    data=register(client)
    denied=client.post('/api/v1/auth/login',json={'email':'ali@example.uz','password':'wrong-password'})
    assert denied.status_code==401
    login=client.post('/api/v1/auth/login',json={'email':'ali@example.uz','password':'secure-password-123'})
    assert login.status_code==200
    assert 'refresh_token' not in login.json()
    assert 'HttpOnly' in login.headers['set-cookie']
    token=data['refresh_token']
    response=client.post('/api/v1/auth/refresh?mobile=true',json={'refresh_token':token})
    assert response.status_code==200
    assert client.post('/api/v1/auth/refresh?mobile=true',json={'refresh_token':token}).status_code==401
    next_token=response.json()['refresh_token']
    assert client.post('/api/v1/auth/logout',json={'refresh_token':next_token}).status_code==200
    assert client.post('/api/v1/auth/refresh?mobile=true',json={'refresh_token':next_token}).status_code==401

def test_unauthorized_and_validation(client):
    assert client.get('/api/v1/tasks').status_code==401
    response=client.post('/api/v1/auth/register',json={'name':'','email':'broken','password':'123'})
    assert response.status_code==422
    assert response.json()['error']['message'].startswith('Kiritilgan')

def test_task_and_user_isolation(client,auth):
    task=client.post('/api/v1/tasks',headers=auth,json={'title':'Dastur yaratish','priority':'yuqori','due_date':'2026-12-01'}).json()
    other=register(client,'other@example.uz');other_auth={'Authorization':'Bearer '+other['access_token']}
    assert client.get('/api/v1/tasks',headers=other_auth).json()['total']==0
    assert client.get('/api/v1/tasks/'+task['id'],headers=other_auth).status_code==404
    assert client.delete('/api/v1/tasks/'+task['id'],headers=other_auth).status_code==404
    assert client.put('/api/v1/tasks/'+task['id'],headers=auth,json={'title':'Dastur yaratish','completed':True}).status_code==200
    assert client.get('/api/v1/tasks?completed=true',headers=auth).json()['total']==1
    assert client.delete('/api/v1/tasks/'+task['id'],headers=auth).status_code==200

def test_memory_permissions_and_history(client,auth):
    data={'title':'Til afzalligi','content':'Men o‘zbekcha gaplashaman','tags':['til'],'use_in_chat':False}
    response=client.post('/api/v1/memories',headers=auth,json=data)
    assert response.status_code==201,response.text
    memory=response.json();assert memory['indexed'] is False
    result=client.get('/api/v1/memories/search?q=o‘zbekcha',headers=auth).json()
    assert len(result['items'])==1 and result['mode']=='text'
    history=client.get('/api/v1/memories/'+memory['id']+'/history',headers=auth).json()
    assert history['items'][0]['action']=='memories:create'

def test_projects_and_cross_owner_reference(client,auth):
    project=client.post('/api/v1/projects',headers=auth,json={'title':'JARVIS','technologies':['Python'],'repository_url':'https://github.com/example/jarvis'}).json()
    other=register(client,'other@example.uz');headers={'Authorization':'Bearer '+other['access_token']}
    assert client.post('/api/v1/tasks',headers=headers,json={'title':'Forbidden','project_id':project['id']}).status_code==404
    assert client.put('/api/v1/projects/'+project['id'],headers=auth,json={'title':'Yangilangan'}).status_code==200
    assert client.delete('/api/v1/projects/'+project['id'],headers=auth).status_code==200

def test_knowledge_validation_and_summary(client,auth):
    assert client.post('/api/v1/knowledge/upload',headers=auth,files={'file':('run.exe',b'anything','application/octet-stream')}).status_code==415
    assert client.post('/api/v1/knowledge/upload',headers=auth,files={'file':('fake.pdf',b'not a pdf','application/pdf')}).status_code==422
    assert client.post('/api/v1/knowledge/upload',headers=auth,files={'file':('big.txt',b'x'*(5*1024*1024+1),'text/plain')}).status_code==413
    response=client.post('/api/v1/knowledge/upload',headers=auth,files={'file':('eslatma.txt','O‘zbekcha bilimlar'.encode(),'text/plain')})
    assert response.status_code==201,response.text
    document=response.json()
    result=client.post('/api/v1/knowledge/'+document['id']+'/summarize',headers=auth)
    assert result.status_code==200 and '[SINOV JAVOBI]' in result.json()['summary']

def test_mock_stream_and_conversation_storage(client,auth):
    response=client.post('/api/v1/chat/stream',headers=auth,json={'content':'Salom JARVIS'})
    assert response.status_code==200,response.text
    import json
    events=[json.loads(line) for line in response.text.splitlines()]
    assert events[0]['type']=='start' and events[-1]['type']=='done'
    assert '[SINOV JAVOBI]' in events[1]['content']
    conversation_id=events[0]['conversation_id']
    messages=client.get('/api/v1/conversations/'+conversation_id+'/messages',headers=auth).json()['items']
    assert len(messages)==2
    again=client.post('/api/v1/chat/stream',headers=auth,json={'content':'Salom JARVIS','conversation_id':conversation_id,'regenerate':True})
    assert '"type": "done"' in again.text
    assert len(client.get('/api/v1/conversations/'+conversation_id+'/messages',headers=auth).json()['items'])==2
    other=register(client,'other@example.uz');headers={'Authorization':'Bearer '+other['access_token']}
    assert client.get('/api/v1/conversations/'+conversation_id+'/messages',headers=headers).status_code==404
    assert client.post('/api/v1/chat/stream',headers=headers,json={'content':'Salom','conversation_id':conversation_id}).status_code==404
    assert client.delete('/api/v1/conversations/'+conversation_id,headers=auth).status_code==200

def test_dashboard_business_and_settings(client,auth):
    assert client.get('/api/v1/dashboard',headers=auth).json()['counts']['tasks']==0
    assert client.post('/api/v1/business',headers=auth,json={'title':'Daromad','kind':'daromad','amount':1500,'date':'2026-11-07'}).status_code==201
    assert client.put('/api/v1/settings',headers=auth,json={'theme':'light'}).status_code==200
    assert client.get('/api/v1/settings',headers=auth).json()['theme']=='light'
    assert client.get('/api/v1/ai/status',headers=auth).json()['provider']=='mock'
    assert client.put('/api/v1/ai/settings',headers=auth,json={'model':'not-installed'}).status_code==422
    assert client.post('/api/v1/voice/speak',headers=auth,json={'text':'Salom'}).status_code==503

def test_cors_and_rate_limit(client):
    assert client.post('/api/v1/auth/logout',headers={'Origin':'https://evil.example'},json={}).status_code==403
    for _ in range(20): client.post('/api/v1/auth/login',json={})
    assert client.post('/api/v1/auth/login',json={}).status_code==429

def test_sensitive_fields_never_exposed(client,auth):
    response=client.get('/api/v1/users/me',headers=auth)
    assert set(response.json())=={'id','name','email'}
    assert client.post('/api/v1/tasks',headers=auth,json={'title':'bad','owner_id':'arbitrary'}).status_code==422

def test_knowledge_search_and_project_notes(client,auth):
    client.post('/api/v1/knowledge',headers=auth,json={'title':'Yo‘riqnoma','content':'Python uchun maxfiy bilim'})
    assert len(client.get('/api/v1/knowledge/search?q=Python',headers=auth).json()['items'])==1
    project=client.post('/api/v1/projects',headers=auth,json={'title':'Loyiha'}).json()
    note=client.post('/api/v1/projects/'+project['id']+'/notes',headers=auth,json={'content':'Birinchi qayd'}).json()
    assert client.get('/api/v1/projects/'+project['id']+'/notes',headers=auth).json()['items'][0]['content']=='Birinchi qayd'
    assert client.delete('/api/v1/projects/'+project['id']+'/notes/'+note['id'],headers=auth).status_code==200
    response=client.post('/api/v1/projects/analyze-code',headers=auth,json={'text':'print(1)'})
    assert response.status_code==200 and '[SINOV JAVOBI]' in response.json()['analysis']
    report=client.get('/api/v1/business/report/summary?ai=true',headers=auth).json()
    assert report['balance']==0 and '[SINOV JAVOBI]' in report['summary']

def test_memory_opt_out_not_returned_to_chat_tools(client,auth):
    client.post('/api/v1/memories',headers=auth,json={'title':'Private','content':'Maxfiy','use_in_chat':False})
    from app.core.database import get_db
    from app.main import app
    from app.memory.service import search_memories
    import asyncio
    user=client.get('/api/v1/users/me',headers=auth).json()
    generator=app.dependency_overrides[get_db]();db=next(generator)
    try:
        rows,_=asyncio.run(search_memories(db,user['id'],'Maxfiy',chat_only=True))
        assert rows==[]
    finally:generator.close()

def test_memory_and_document_user_isolation(client,auth):
    memory=client.post('/api/v1/memories',headers=auth,json={'title':'Sir','content':'Shaxsiy xotira'}).json()
    document=client.post('/api/v1/knowledge',headers=auth,json={'title':'Sirli hujjat','content':'Shaxsiy hujjat'}).json()
    other=register(client,'reader@example.uz');headers={'Authorization':'Bearer '+other['access_token']}
    assert client.get('/api/v1/memories/search?q=Shaxsiy',headers=headers).json()['items']==[]
    assert client.get('/api/v1/memories/'+memory['id'],headers=headers).status_code==404
    assert client.get('/api/v1/knowledge/search?q=Shaxsiy',headers=headers).json()['items']==[]
    assert client.post('/api/v1/knowledge/'+document['id']+'/summarize',headers=headers).status_code==404

def test_installed_model_settings_are_persisted_and_private(client,auth,monkeypatch):
    import app.api.routes as routes
    from app.providers.ollama import MockAIProvider
    class InstalledProvider(MockAIProvider):
        async def health_check(self):return {'provider':'mock','connected':True,'models':['qwen3:4b'],'embedding_ready':False}
    monkeypatch.setattr(routes,'provider',lambda *args:InstalledProvider())
    response=client.put('/api/v1/ai/settings',headers=auth,json={'model':'qwen3:4b','temperature':0.3,'context_length':8192,'system_prompt':'Misol keltiring.'})
    assert response.status_code==200
    settings=client.get('/api/v1/ai/status',headers=auth).json()['settings']
    assert settings['model']=='qwen3:4b' and settings['temperature']==0.3 and settings['context_length']==8192
    other=register(client,'settings@example.uz');headers={'Authorization':'Bearer '+other['access_token']}
    assert client.get('/api/v1/ai/status',headers=headers).json()['settings']['model']=='qwen3:8b'

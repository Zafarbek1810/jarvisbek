"""Run against a local JARVIS instance. Creates and removes only random QA accounts."""
import asyncio
import secrets
import uuid
import httpx
from sqlalchemy import delete, text
from app.core.database import SessionLocal
from app.models import User

async def main():
    accounts=[]
    async with httpx.AsyncClient(base_url='http://localhost:8010',timeout=30) as client:
        assert (await client.get('/health')).status_code==200
        assert (await client.get('/ready')).status_code==200
        try:
            sessions=[]
            for _ in range(2):
                email='qa-'+uuid.uuid4().hex+'@example.uz'
                result=await client.post('/api/v1/auth/register?mobile=true',json={'name':'Tekshiruv','email':email,'password':secrets.token_urlsafe(24)})
                assert result.status_code==201,result.text
                data=result.json();accounts.append(data['user']['id']);
                refreshes=await asyncio.gather(*[client.post('/api/v1/auth/refresh?mobile=true',json={'refresh_token':data['refresh_token']}) for _ in range(2)])
                assert sorted(r.status_code for r in refreshes)==[200,401]
                sessions.append({'Authorization':'Bearer '+data['access_token']})
            headers,other=sessions
            response=await client.post('/api/v1/tasks',headers=headers,json={'title':'PostgreSQL tekshiruvi'})
            assert response.status_code==201,response.text
            task=response.json()
            assert (await client.get('/api/v1/tasks/'+task['id'],headers=other)).status_code==404
            assert (await client.get('/api/v1/tasks',headers=headers)).json()['total']==1
            memory=await client.post('/api/v1/memories',headers=headers,json={'title':'O‘zbekcha xotira','content':'Mahalliy ma’lumotlar saqlanadi'})
            assert memory.status_code==201,memory.text
            found=await client.get('/api/v1/memories/search?q=Mahalliy',headers=headers)
            assert len(found.json()['items'])==1
            status=(await client.get('/api/v1/ai/status',headers=headers)).json()
            assert status['provider']=='ollama' and status['connected']
            # No model download: missing model must produce an honest localized error.
            stream=await client.post('/api/v1/chat/stream',headers=headers,json={'content':'Salom'})
            assert stream.status_code==200
            assert '"type": "error"' in stream.text if not status['model_ready'] else '"type": "done"' in stream.text
            print('PASS: health, PostgreSQL, Redis, registration, task persistence, owner isolation, memory text search, Ollama status, chat error handling.')
            print('Installed models:',status['models'])
            with SessionLocal() as db:
                value=db.scalar(text("SELECT '[1,0,0]'::vector <=> '[1,0,0]'::vector"));assert value==0
                print('PASS: pgvector cosine-distance SQL.')
        finally:
            with SessionLocal() as db:
                db.execute(delete(User).where(User.id.in_(accounts),User.email.like('qa-%@example.uz')));db.commit()

asyncio.run(main())

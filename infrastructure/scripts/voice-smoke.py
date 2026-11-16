"""Local synthetic Uzbek voice round trip; never records the user's microphone."""
import asyncio
import json
import secrets
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx
from sqlalchemy import delete

from app.core.database import SessionLocal
from app.models import User
from app.providers.voice import synthesize_local, run_audio_tool


async def main():
    account_id = None
    email = 'qa-voice-' + uuid.uuid4().hex + '@example.uz'
    report = {'sample': 'provided local audio' if len(sys.argv)>1 else 'synthetic eSpeak Uzbek; human pronunciation not verified', 'formats': {}}
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8010/api/v1', timeout=180) as client:
        try:
            response = await client.post('/auth/register?mobile=true', json={'name': 'Ovoz sinovi', 'email': email, 'password': secrets.token_urlsafe(24)})
            response.raise_for_status()
            data = response.json(); account_id = data['user']['id']
            client.headers['Authorization'] = 'Bearer ' + data['access_token']
            response = await client.get('/voice/status'); response.raise_for_status()
            report['status'] = response.json()
            assert report['status']['stt_configured'] and report['status']['tts_configured'], report
            sample = Path(sys.argv[1]).read_bytes() if len(sys.argv)>1 else await synthesize_local("Salom Jarvis. Ikki qo‘shuv ikki necha bo‘ladi?")
            with tempfile.TemporaryDirectory(prefix='jarvis-voice-test-') as directory:
                root = Path(directory); (root / 'sample.wav').write_bytes(sample)
                for ext, codec, mime in [('webm', 'libopus', 'audio/webm;codecs=opus'), ('m4a', 'aac', 'audio/mp4')]:
                    output = root / ('sample.' + ext)
                    await run_audio_tool('ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(root / 'sample.wav'), '-c:a', codec, str(output))
                    start = time.monotonic()
                    response = await client.post('/voice/transcribe', files={'file': (output.name, output.read_bytes(), mime)})
                    response.raise_for_status(); transcript = response.json()['text']; assert transcript.strip()
                    report['formats'][ext] = {'text': transcript, 'seconds': round(time.monotonic() - start, 2)}
                start = time.monotonic()
                response = await client.post('/chat/stream', json={'content': report['formats']['webm']['text']})
                response.raise_for_status()
                events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
                assert not any(event['type'] == 'error' for event in events), events
                assert any(event['type'] == 'done' for event in events)
                reply = ''.join(event.get('content', '') for event in events if event['type'] == 'delta'); assert reply
                report['reply'] = reply; report['chat_seconds'] = round(time.monotonic() - start, 2)
                response = await client.post('/voice/speak', json={'text': reply[:3000]}); response.raise_for_status()
                assert response.content[:4] == b'RIFF' and response.content[8:12] == b'WAVE'
                Path('.runtime/voice-reply.wav').write_bytes(response.content)
                report['reply_audio_bytes'] = len(response.content)
            Path('.runtime/voice-smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
            print(json.dumps(report, ensure_ascii=False, indent=2))
        finally:
            if account_id:
                with SessionLocal() as db:
                    db.execute(delete(User).where(User.id == account_id, User.email == email)); db.commit()


asyncio.run(main())

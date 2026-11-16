import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import get_settings
from app.providers import voice


def test_voice_upload_formats_and_empty_audio(client, auth, monkeypatch):
    monkeypatch.setattr(get_settings(), 'voice_stt_url', 'http://whisper.test')
    transcribe = AsyncMock(return_value='Salom, bugun nima qilamiz?')
    monkeypatch.setattr(voice, 'transcribe_audio', transcribe)
    for mime in ['audio/webm;codecs=opus', 'audio/mp4', 'audio/x-m4a']:
        response = client.post('/api/v1/voice/transcribe', headers=auth, files={'file': ('voice', b'audio', mime)})
        assert response.status_code == 200, response.text
        assert response.json()['text'] == 'Salom, bugun nima qilamiz?'
    assert client.post('/api/v1/voice/transcribe', headers=auth, files={'file': ('voice', b'', 'audio/webm')}).status_code == 422
    assert client.post('/api/v1/voice/transcribe', headers=auth, files={'file': ('voice', b'text', 'text/plain')}).status_code == 415
    assert transcribe.await_count == 3


def test_local_speech_and_transcription_failures(client, auth, monkeypatch):
    monkeypatch.setattr(get_settings(), 'voice_tts_engine', 'espeak')
    monkeypatch.setattr(get_settings(), 'voice_tts_url', '')
    synthesize = AsyncMock(return_value=b'RIFF-test-WAVE')
    monkeypatch.setattr(voice, 'synthesize_local', synthesize)
    response = client.post('/api/v1/voice/speak', headers=auth, json={'text': 'Salom; $(command)'})
    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/wav'
    synthesize.assert_awaited_once_with('Salom; $(command)')
    synthesize.side_effect = voice.VoiceError('Ovoz yaratilmadi.')
    assert client.post('/api/v1/voice/speak', headers=auth, json={'text': 'Salom'}).status_code == 503


@pytest.mark.asyncio
async def test_normalizes_audio_and_rejects_empty_transcription(monkeypatch):
    real_client = httpx.AsyncClient
    captured = []
    async def convert(*args, **kwargs):
        captured.append(args)
        Path(args[-1]).write_bytes(b'RIFF-WAVE')
        return b''
    def respond(request):
        assert b'audio.wav' in request.content and b'audio/wav' in request.content
        assert b'RIFF-WAVE' in request.content
        return httpx.Response(200, json={'text': '  Salom dunyo!  '})
    monkeypatch.setattr(voice, 'run_audio_tool', convert)
    monkeypatch.setattr(voice, 'get_settings', lambda: SimpleNamespace(voice_stt_url='http://whisper.test'))
    monkeypatch.setattr(voice.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(respond)))
    assert await voice.transcribe_audio(b'compressed webm') == 'Salom dunyo!'
    assert captured[0][0] == 'ffmpeg' and 'pcm_s16le' in captured[0] and '16000' in captured[0]
    directory = Path(captured[0][-1]).parent
    assert not directory.exists()
    monkeypatch.setattr(voice.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'text': '[BLANK_AUDIO]'}))))
    with pytest.raises(voice.VoiceError, match='Nutq eshitilmadi'):
        await voice.transcribe_audio(b'silence')


@pytest.mark.asyncio
async def test_audio_process_timeout_kills_and_reaps(monkeypatch):
    class Process:
        returncode = None
        killed = False
        calls = 0
        def kill(self):
            self.killed = True
            self.returncode = -9
        async def communicate(self, data=None):
            self.calls += 1
            if self.calls == 1: await asyncio.sleep(10)
            return b'', b''
    process = Process()
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', AsyncMock(return_value=process))
    with pytest.raises(voice.VoiceError, match='vaqti tugadi'):
        await voice.run_audio_tool('ffmpeg', timeout=0.01)
    assert process.killed and process.calls == 2


@pytest.mark.asyncio
async def test_voice_status_checks_service_health(monkeypatch):
    cfg = SimpleNamespace(voice_stt_url='http://whisper.test', voice_tts_url='', voice_tts_engine='espeak')
    monkeypatch.setattr(voice, 'get_settings', lambda: cfg)
    monkeypatch.setattr(voice.shutil, 'which', lambda name: '/local/bin/' + name)
    real_client = httpx.AsyncClient
    monkeypatch.setattr(voice.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(lambda request: httpx.Response(503))))
    status = await voice.voice_status()
    assert status['stt_configured'] is False and status['tts_configured'] is True
    monkeypatch.setattr(voice.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'status': 'ok'}))))
    assert (await voice.voice_status())['stt_configured'] is True


def test_uzbek_normalization_preserves_names_and_mixed_script():
    from app.core.uzbek import normalize_uzbek

    assert normalize_uzbek('  O‘tkir  G’ulomov Chrome’da «привет» dedi.  ') == (
        'Oʻtkir Gʻulomov Chrome’da «привет» dedi.'
    )


def test_local_voice_rejects_external_inference():
    from app.core.config import Settings

    with pytest.raises(ValueError, match='VOICE_TTS_ENGINE'):
        Settings(voice_local_only=True, voice_allow_edge_tts=False, voice_tts_engine='edge')
    with pytest.raises(ValueError, match='loopback'):
        Settings(voice_local_only=True, voice_tts_engine='espeak', voice_stt_url='https://example.com')

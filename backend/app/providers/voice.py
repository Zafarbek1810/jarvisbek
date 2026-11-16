"""Local audio tools. Fixed executables/arguments only; audio never enters a shell."""
import asyncio
import wave
from array import array
import shutil
import tempfile
from importlib.util import find_spec
from pathlib import Path
from typing import Literal, get_args
from xml.sax.saxutils import escape

import httpx

from app.core.config import get_settings
from app.core.uzbek import normalize_uzbek
from app.providers import stt


AzureVoice = Literal['uz-UZ-SardorNeural', 'uz-UZ-MadinaNeural']
AZURE_VOICES = get_args(AzureVoice)


class VoiceError(Exception):
    pass


async def run_audio_tool(*args: str, input_data: bytes | None = None, timeout: int = 30) -> bytes:
    try:
        process = await asyncio.create_subprocess_exec(
            *args, stdin=asyncio.subprocess.PIPE if input_data is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        raise VoiceError('Mahalliy audio dasturi topilmadi. Ovoz sozlamalarini tekshiring.') from exc
    try:
        output, _ = await asyncio.wait_for(process.communicate(input_data), timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
        if process.returncode is None:
            process.kill()
        await process.communicate()
        if isinstance(exc, asyncio.CancelledError):
            raise
        raise VoiceError('Ovozni qayta ishlash vaqti tugadi. Qisqaroq yozuv bilan qayta urinib ko‘ring.') from exc
    if process.returncode:
        raise VoiceError('Ovoz faylini o‘qib bo‘lmadi. Qayta yozib ko‘ring.')
    return output


async def transcribe_audio(data: bytes, model: str | None = None) -> str:
    cfg = get_settings()
    # Both browser WebM/MP4 and mobile M4A are normalized before Whisper.
    with tempfile.TemporaryDirectory(prefix='jarvis-voice-') as directory:
        source, target = Path(directory) / 'input', Path(directory) / 'audio.wav'
        source.write_bytes(data)
        local_only = getattr(cfg, 'voice_local_only', False)
        filters = ['-af', 'highpass=f=80,lowpass=f=7600'] if local_only else []
        await run_audio_tool('ffmpeg', '-nostdin', '-v', 'error', '-y', '-protocol_whitelist', 'file,pipe', '-i', str(source),
                             '-t', '60', '-vn', *filters, '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(target))
        if local_only:
            with wave.open(str(target), 'rb') as audio:
                samples = array('h', audio.readframes(audio.getnframes()))
            if len(samples) < 2400 or max(map(abs, samples), default=0) < 128:
                raise VoiceError('Nutq eshitilmadi. Mikrofonga yaqinroq gapiring.')
        if model and model != cfg.voice_stt_model:
            path = stt.model_path(model)
            if path is None or not path.is_file():
                raise VoiceError('Tanlangan mahalliy STT modeli o‘rnatilmagan.')
            output = Path(directory) / 'transcript'
            await run_audio_tool('whisper-cli', '-m', str(path), '-f', str(target),
                                 '-l', 'uz', '-t', '4', '-nt', '-nf', '-otxt', '-of', str(output),
                                 *stt.device_args(), timeout=90)
            try:
                text = output.with_suffix('.txt').read_text(encoding='utf-8')
            except OSError as exc:
                raise VoiceError('Mahalliy STT matn qaytarmadi.') from exc
        else:
            try:
                async with httpx.AsyncClient(timeout=120, trust_env=not local_only) as client:
                    response = await client.post(cfg.voice_stt_url.rstrip('/') + '/inference',
                        files={'file': ('audio.wav', target.read_bytes(), 'audio/wav')},
                        data={'language': 'uz', 'response_format': 'json', 'temperature': '0.0',
                              'temperature_inc': '0.0'})
                    response.raise_for_status()
                    text = response.json()['text']
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                raise VoiceError('Nutqni tanish bajarilmadi. Mahalliy Whisper xizmatini tekshiring.') from exc
    if not isinstance(text, str) or not text.strip() or text.strip() in ('[BLANK_AUDIO]', '[Silence]'):
        raise VoiceError('Nutq eshitilmadi. Mikrofonga yaqinroq gapirib, qayta urinib ko‘ring.')
    return normalize_uzbek(text)


async def synthesize_local(text: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix='jarvis-tts-') as directory:
        output = Path(directory) / 'reply.wav'
        await run_audio_tool('espeak-ng', '-v', 'uz', '-s', str(get_settings().voice_tts_speed),
                             '-w', str(output), '--stdin',
                             input_data=normalize_uzbek(text).replace('ʻ', "'").encode('utf-8'))
        try:
            return output.read_bytes()
        except OSError as exc:
            raise VoiceError('Mahalliy ovoz fayli yaratilmadi.') from exc


async def synthesize_azure(text: str, selected_voice: AzureVoice) -> bytes:
    cfg = get_settings()
    if not (cfg.azure_speech_key and cfg.azure_speech_region):
        raise VoiceError('Azure Speech kaliti va hududini sozlang.')
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="uz-UZ">'
        f'<voice name="{selected_voice}">{escape(text)}</voice></speak>'
    )
    endpoint = f'https://{cfg.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1'
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(endpoint, content=ssml.encode('utf-8'), headers={
                'Ocp-Apim-Subscription-Key': cfg.azure_speech_key,
                'Content-Type': 'application/ssml+xml',
                'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm',
                'User-Agent': 'Jarvis',
            })
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise VoiceError('Azure ovoz yaratmadi. Speech kaliti, hududi va xizmat holatini tekshiring.') from exc
    if not response.content.startswith(b'RIFF') or response.content[8:12] != b'WAVE':
        raise VoiceError('Azure yaroqli WAV ovozini qaytarmadi.')
    return response.content


async def synthesize_edge(text: str, selected_voice: AzureVoice) -> bytes:
    if find_spec('edge_tts') is None:
        raise VoiceError('Edge TTS paketi o‘rnatilmagan.')

    from edge_tts import Communicate

    async def collect_audio() -> bytes:
        audio = bytearray()
        async for chunk in Communicate(text, selected_voice).stream():
            if chunk['type'] == 'audio':
                audio.extend(chunk['data'])
        return bytes(audio)

    try:
        audio = await asyncio.wait_for(collect_audio(), timeout=30)
    except Exception as exc:
        raise VoiceError('Edge TTS ovoz yaratmadi. Internet ulanishini tekshirib qayta urining.') from exc
    if not audio:
        raise VoiceError('Edge TTS ovoz qaytarmadi.')
    return audio


async def voice_status() -> dict:
    cfg = get_settings()
    stt_ready = False
    if cfg.voice_stt_url and shutil.which('ffmpeg'):
        try:
            async with httpx.AsyncClient(timeout=2, trust_env=not getattr(cfg, 'voice_local_only', False)) as client:
                response = await client.get(cfg.voice_stt_url.rstrip('/') + '/health')
                stt_ready = response.is_success
        except httpx.HTTPError:
            pass
    tts_ready = bool(cfg.voice_tts_url) or (cfg.voice_tts_engine == 'espeak' and bool(shutil.which('espeak-ng')))
    message = ('Ovoz xizmati tayyor. O‘zbekcha tanish sifati talaffuzga bog‘liq.' if stt_ready
               else 'Nutqni tanish xizmati ishlamayapti. Mahalliy Whisper xizmatini ishga tushiring.')
    azure_enabled = cfg.voice_tts_engine == 'azure' and not cfg.voice_tts_url
    edge_enabled = cfg.voice_tts_engine == 'edge' and not cfg.voice_tts_url
    local_voices = []
    if cfg.voice_tts_engine == 'speecht5' and cfg.voice_tts_url:
        try:
            async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
                tts_ready = (await client.get(cfg.voice_tts_url.rstrip('/') + '/health')).is_success
        except httpx.HTTPError:
            tts_ready = False
        if tts_ready:
            local_voices.append({'id': 'speecht5', 'label': 'SpeechT5 Uzbek'})
        if shutil.which('espeak-ng'):
            local_voices.append({'id': 'espeak', 'label': 'eSpeak NG Uzbek'})
        tts_ready = bool(local_voices)
        message += ' Ovoz mahalliy yaratiladi.' if tts_ready else ' Mahalliy TTS serveri ishlamayapti.'
    elif edge_enabled:
        tts_ready = find_spec('edge_tts') is not None
        message += (' Javob matni ovoz yaratish uchun Microsoft Edge xizmatiga yuboriladi.' if tts_ready
                    else ' Edge TTS paketini o‘rnating.')
    elif azure_enabled:
        tts_ready = bool(cfg.azure_speech_key and cfg.azure_speech_region)
        message += (' Javob matni ovoz yaratish uchun Azure Speech xizmatiga yuboriladi.' if tts_ready
                    else ' Azure Speech kaliti va hududini sozlang.')
    elif cfg.voice_tts_engine == 'espeak' and not cfg.voice_tts_url:
        message += ' Javob mahalliy, robotga o‘xshash ovozda o‘qiladi.'
    elif not tts_ready:
        message += ' Javob hozircha faqat matnda ko‘rinadi.'
    return {
            'local_only': getattr(cfg, 'voice_local_only', False),
            'stt_model': getattr(cfg, 'voice_stt_model', 'small'),
            'stt_device': getattr(cfg, 'voice_stt_device', 'auto'),
            'stt_models': stt.model_options(),
            'local_voices': local_voices,
            'tts_engine': cfg.voice_tts_engine,
            'stt_configured': stt_ready, 'tts_configured': tts_ready,
            'tts_voices': AZURE_VOICES if (azure_enabled or edge_enabled) and tts_ready else [],
            'uzbek_verified': False, 'message': message}

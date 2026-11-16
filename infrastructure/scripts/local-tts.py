"""Offline SpeechT5/HiFi-GAN loopback adapter for Jarvis."""
import argparse
import io
import json
import os
import sys
import wave
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.uzbek import normalize_uzbek_for_speech

MODELS = ROOT / '.runtime/models'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'


@lru_cache(maxsize=1)
def load(device):
    import torch
    from transformers import SpeechT5ForTextToSpeech, SpeechT5HifiGan, SpeechT5Tokenizer

    torch.set_num_threads(4)
    if device == 'mps' and not torch.backends.mps.is_available():
        raise RuntimeError('Metal/MPS mavjud emas. CPU rejimini tanlang.')
    path = MODELS / 'speecht5-uz'
    tokenizer = SpeechT5Tokenizer.from_pretrained(path, local_files_only=True)
    model = SpeechT5ForTextToSpeech.from_pretrained(path, local_files_only=True).eval().to(device)
    vocoder = SpeechT5HifiGan.from_pretrained(MODELS / 'speecht5-vocoder', local_files_only=True).eval().to(device)
    return torch, tokenizer, model, vocoder


def synthesize(text, device):
    torch, tokenizer, model, vocoder = load(device)
    words = normalize_uzbek_for_speech(text).split()
    chunks = []
    current = ''
    for word in words:
        if current and len(current) + len(word) + 1 > 180:
            chunks.append(current)
            current = ''
        current = f'{current} {word}'.strip()
    if current:
        chunks.append(current)
    if not chunks:
        raise ValueError('Matn bo‘sh.')
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as output, torch.inference_mode():
        output.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        # Fixed neutral conditioning. No reference recording is required.
        speaker = torch.zeros((1, model.config.speaker_embedding_dim), device=device)
        for chunk in chunks:
            ids = tokenizer(chunk, return_tensors='pt', truncation=True, max_length=256).input_ids.to(device)
            audio = model.generate_speech(ids, speaker, vocoder=vocoder, maxlenratio=12)
            pcm = (audio.cpu().clamp(-1, 1) * 32767).to(torch.int16)
            output.writeframes(pcm.numpy().astype('<i2', copy=False).tobytes())
    return stream.getvalue()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/health':
            self.send_error(404)
            return
        files = ('speecht5-uz/model.safetensors', 'speecht5-vocoder/pytorch_model.bin')
        if not all((MODELS / file).is_file() for file in files):
            self.send_error(503, 'Local model files missing')
            return
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path != '/synthesize':
            self.send_error(404)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 24000:
                raise ValueError
            payload = json.loads(self.rfile.read(size))
            text = payload['text']
            if not isinstance(text, str) or not 1 <= len(text.strip()) <= 3000:
                raise ValueError
        except (TypeError, ValueError, KeyError):
            self.send_error(400, 'Invalid speech text')
            return
        try:
            audio = synthesize(text, self.server.device)
        except Exception as exc:
            print(f'TTS failed: {type(exc).__name__}', file=sys.stderr)
            self.send_error(503, 'Local TTS failed')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'audio/wav')
        self.send_header('Content-Length', str(len(audio)))
        self.end_headers()
        self.wfile.write(audio)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', choices=('cpu', 'mps'), default='cpu')
    parser.add_argument('--port', type=int, default=8181)
    parser.add_argument('--sample', help='Sinov uchun matn')
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/speecht5-sample.wav')
    args = parser.parse_args()
    if args.sample:
        args.output.write_bytes(synthesize(args.sample, args.device))
    else:
        with HTTPServer(('127.0.0.1', args.port), Handler) as server:
            server.device = args.device
            server.serve_forever()

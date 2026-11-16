"""Compare installed local Whisper models against a user-supplied transcript."""
import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from app.core.uzbek import normalize_uzbek
from app.providers import stt, voice


def distance(reference, actual):
    previous = list(range(len(actual) + 1))
    for index, expected in enumerate(reference, 1):
        current = [index]
        for column, observed in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (expected != observed)))
        previous = current
    return previous[-1]


def scoring_text(text):
    text = normalize_uzbek(text).casefold()
    return ' '.join(re.sub(r"[^\wʻ']+", ' ', text).split())


async def evaluate(args):
    reference_text = args.reference or input('To‘g‘ri matnni kiriting: ')
    reference = scoring_text(reference_text)
    if not reference:
        raise SystemExit('To‘g‘ri matn bo‘sh.')
    with tempfile.TemporaryDirectory(prefix='jarvis-eval-') as directory:
        root = Path(directory)
        audio = root / 'input.wav'
        if args.audio:
            source = ['-protocol_whitelist', 'file,pipe', '-i', str(args.audio.resolve())]
        else:
            print(f'Mikrofon {args.seconds} soniya yozadi. Gapiring.', flush=True)
            source = ['-f', 'avfoundation', '-i', ':' + args.microphone]
        await voice.run_audio_tool(
            'ffmpeg', '-nostdin', '-v', 'error', *source, '-t', str(args.seconds),
            '-vn', '-af', 'highpass=f=80,lowpass=f=7600',
            '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(audio), timeout=args.seconds + 15,
        )
        for name in args.models:
            model = stt.model_path(name)
            if model is None or not model.is_file():
                print(f'{name}: model fayli topilmadi.', file=sys.stderr)
                continue
            output = root / name
            started = time.monotonic()
            await voice.run_audio_tool(
                'whisper-cli', '-m', str(model), '-f', str(audio), '-l', 'uz', '-t', '4',
                '-nt', '-nf', '-otxt', '-of', str(output),
                *(['--no-gpu'] if args.device == 'cpu' else []), timeout=120,
            )
            elapsed = time.monotonic() - started
            text = output.with_suffix('.txt').read_text().strip()
            hypothesis = scoring_text(text)
            reference_chars = reference.replace(' ', '')
            result = {
                'date': datetime.now(timezone.utc).isoformat(),
                'region': args.region, 'style': args.style, 'model': name,
                'device': args.device, 'elapsed_seconds': round(elapsed, 3),
                'wer': round(distance(reference.split(), hypothesis.split()) / len(reference.split()), 4),
                'cer': round(distance(reference_chars, hypothesis.replace(' ', '')) / len(reference_chars), 4),
            }
            if args.save_text:
                result.update(reference=reference_text, transcript=text)
            line = json.dumps(result, ensure_ascii=False)
            print(line, flush=True)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open('a', encoding='utf-8') as handle:
                    handle.write(line + '\n')


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, help='Mavjud mahalliy audio')
    parser.add_argument('--microphone', default='0', help='macOS AVFoundation mikrofon indeksi')
    parser.add_argument('--seconds', type=int, choices=range(1, 61), default=30, metavar='1–60')
    parser.add_argument('--reference')
    parser.add_argument('--region', choices=['xorazm', 'toshkent', 'fargona', 'samarqand', 'boshqa'], default='boshqa')
    parser.add_argument('--style', choices=['tabiiy', 'tez', 'sekin', 'aralash', 'shovqin'], default='tabiiy')
    parser.add_argument('--models', nargs='+', choices=stt.MODELS, default=['tiny', 'small', 'kotib'])
    parser.add_argument('--device', choices=['auto', 'cpu'], default='auto')
    parser.add_argument('--output', type=Path, help='Mahalliy JSONL hisobot')
    parser.add_argument('--save-text', action='store_true', help='Hisobotga matnlarni ham yozish')
    try:
        asyncio.run(evaluate(parser.parse_args()))
    except voice.VoiceError as exc:
        raise SystemExit(str(exc)) from exc

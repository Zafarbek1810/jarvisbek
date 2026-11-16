"""Download and convert a NavAI Uzbek Whisper model locally."""
import argparse
import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / '.runtime/models/uzbek-tiny'
SHA256 = '95102b41a7e84ced74f1e640ad3ca00fc6c48b96419642345de3b0bd829936c8'
BASE = 'https://huggingface.co/navai-uz/whisper-tiny-uzbek/resolve/main/'


def download(url, target):
    temporary = target.with_suffix(target.suffix + '.download')
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
        while block := response.read(1024 * 1024):
            output.write(block)
    temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('size', choices=['tiny', 'small', 'kotib', 'speecht5'], nargs='?', default='tiny')
    size = parser.parse_args().size
    if size == 'speecht5':
        setup_speecht5()
        return
    try:
        import safetensors.numpy  # noqa: F401
    except ImportError:
        raise SystemExit('Avval: .venv/bin/pip install -r infrastructure/requirements-voice-tools.txt')
    if size != 'tiny':
        setup_extended(size)
        return
    MODEL.mkdir(parents=True, exist_ok=True)
    weights = MODEL / 'model.safetensors'
    if not weights.exists() or hashlib.sha256(weights.read_bytes()).hexdigest() != SHA256:
        print('NavAI Uzbek Whisper tiny: 151 MB yuklanmoqda…', flush=True)
        download(BASE + 'model.safetensors', weights)
    if hashlib.sha256(weights.read_bytes()).hexdigest() != SHA256:
        raise SystemExit('Model SHA256 mos kelmadi. Fayl ishlatilmadi.')
    for name in ['config.json', 'vocab.json', 'LICENSE', 'NOTICE']:
        download(BASE + name, MODEL / name)
    download('https://raw.githubusercontent.com/openai/whisper/main/whisper/assets/mel_filters.npz', MODEL / 'mel_filters.npz')
    output = MODEL.parent / 'ggml-tiny-uzbek.bin'
    subprocess.run([sys.executable, str(ROOT / 'infrastructure/scripts/convert-uzbek-whisper.py'), str(MODEL), str(output)], check=True)
    print('Model tayyor. ./infrastructure/scripts/voice.sh orqali ishga tushiring.')


def setup_extended(size):
    repo, revision, folder = {
        'small': ('navai-uz/whisper-small-uzbek', '91dc67b730ff0c5274fb7deac352b87b455cb3fd', 'uzbek-small'),
        'kotib': ('Kotib/uzbek_stt_v1', '0e23951', 'kotib'),
    }[size]
    base = f'https://huggingface.co/{repo}/resolve/{revision}/'
    directory = MODEL.parent / folder
    directory.mkdir(parents=True, exist_ok=True)
    for name in ('config.json', 'vocab.json', 'model.safetensors'):
        target = directory / name
        if not target.exists():
            print(f'{repo}: {name} yuklanmoqda…', flush=True)
            download(base + name, target)
    mel = directory / 'mel_filters.npz'
    if not mel.exists():
        if (MODEL / mel.name).exists():
            shutil.copyfile(MODEL / mel.name, mel)
        else:
            download('https://raw.githubusercontent.com/openai/whisper/main/whisper/assets/mel_filters.npz', mel)
    output = directory.parent / f'ggml-{size}-uzbek.bin'
    temporary = output.with_suffix('.bin.download')
    subprocess.run([sys.executable, str(ROOT / 'infrastructure/scripts/convert-uzbek-whisper.py'),
                    str(directory), str(temporary)], check=True)
    temporary.replace(output)
    print('Whisper modeli tayyor. ./infrastructure/scripts/voice.sh orqali ishga tushiring.')


def setup_speecht5():
    checkpoints = (
        ('AbrorBalxiyev/uzbek-tts-model', 'f3960aa8604404df1276ed0b880c9366cc56c630', 'speecht5-uz',
         ('config.json', 'spm_char.model', 'tokenizer_config.json', 'special_tokens_map.json',
          'added_tokens.json', 'model.safetensors')),
        ('microsoft/speecht5_hifigan', 'bb6f429406e86a9992357a972c0698b22043307d', 'speecht5-vocoder',
         ('config.json', 'pytorch_model.bin')),
    )
    for repo, revision, folder, files in checkpoints:
        directory = MODEL.parent / folder
        directory.mkdir(parents=True, exist_ok=True)
        for name in files:
            target = directory / name
            if not target.is_file():
                print(f'{repo}: {name} yuklanmoqda…', flush=True)
                download(f'https://huggingface.co/{repo}/resolve/{revision}/{name}', target)


if __name__ == '__main__':
    main()

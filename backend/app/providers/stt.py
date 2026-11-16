"""Known Whisper models that can be selected without accepting arbitrary paths."""
import shutil
from pathlib import Path

from app.core.config import get_settings

MODEL_DIRECTORY = Path(__file__).resolve().parents[3] / '.runtime/models'
MODELS = {
    'small': ('NavAI Uzbek Small', 'ggml-small-uzbek.bin'),
    'tiny': ('NavAI Uzbek Tiny', 'ggml-tiny-uzbek.bin'),
    'kotib': ('Kotib Uzbek Medium', 'ggml-kotib-uzbek.bin'),
}


def model_options() -> list[dict[str, str]]:
    if not shutil.which('whisper-cli'):
        return []
    return [
        {'id': key, 'label': label}
        for key, (label, filename) in MODELS.items()
        if (MODEL_DIRECTORY / filename).is_file()
    ]


def model_path(model: str) -> Path | None:
    if model in MODELS:
        return MODEL_DIRECTORY / MODELS[model][1]
    return None


def device_args() -> list[str]:
    return ['--no-gpu'] if get_settings().voice_stt_device == 'cpu' else []

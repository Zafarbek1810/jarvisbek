#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
DEFAULT_MODEL=.runtime/models/ggml-small-uzbek.bin
if [ ! -s "$DEFAULT_MODEL" ]; then
  DEFAULT_MODEL=.runtime/models/ggml-tiny-uzbek.bin
fi
MODEL=${JARVIS_WHISPER_MODEL:-$DEFAULT_MODEL}
if ! command -v whisper-server >/dev/null 2>&1; then
  echo 'whisper-server topilmadi. macOS: brew install whisper-cpp ffmpeg espeak-ng' >&2
  exit 1
fi
if [ ! -s "$MODEL" ]; then
  echo "Whisper modeli topilmadi: $MODEL. docs/VOICE.md dagi yuklash buyrug‘ini bajaring." >&2
  exit 1
fi
# Only loopback: clients use the authenticated JARVIS API, never this raw service.
set --
case "${JARVIS_WHISPER_DEVICE:-auto}" in
  cpu) set -- --no-gpu ;;
  auto) ;;
  *) echo 'JARVIS_WHISPER_DEVICE: auto yoki cpu bo‘lishi kerak.' >&2; exit 1 ;;
esac
exec whisper-server --host 127.0.0.1 --port 8178 --model "$MODEL" --language uz --threads 4 --no-timestamps "$@"

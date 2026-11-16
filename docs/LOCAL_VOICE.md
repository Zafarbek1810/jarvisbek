# Jarvis mahalliy o‘zbekcha ovoz rejimi

Jarvis vebi Next.js va TypeScript’da, mobil ilova Expo’da, backend FastAPI va Python’da ishlaydi. Suhbatlar PostgreSQL’da saqlanadi, fon ishlari Redis va Celery orqali bajariladi. Ovoz rejimi mavjud sessiya, suhbat va macOS vositalaridan foydalanadi.

## Model tanlovi

| Komponent | Model va runtime | Resurs va litsenziya |
| --- | --- | --- |
| Asosiy STT | NavAI Uzbek Whisper Small, whisper.cpp | 487 MB FP16, Apple Metal yoki CPU. Model Apache-2.0, runtime MIT. |
| Tez STT | NavAI Uzbek Whisper Tiny, whisper.cpp | 78 MB FP16, xotira kam bo‘lganda. Model Apache-2.0. |
| Sinov STT | Kotib Uzbek Whisper Medium, whisper.cpp | 3,06 GB manba og‘irliklari, konvertatsiyadan keyin taxminan 1,53 GB FP16. Model Apache-2.0. |
| Muqobil STT | Gearnode Qwen3-ASR Uzbek v2 | 1,7B parametr, Apache-2.0. Model kartasida CUDA va Flash Attention misoli berilgan. macOS CPU/MPS ishlashi va sifati bu loyihada tasdiqlanmagan. |
| Suhbat | Ollama va Qwen3 4B | Lokal kvantlangan fayl 2,5 GB. Qwen3 Apache-2.0, Ollama MIT. |
| Mahalliy TTS | eSpeak NG yoki SpeechT5 Uzbek + HiFi-GAN | eSpeak GPL-3.0-or-later va CPU’da ishlaydi. SpeechT5 va HiFi-GAN MIT, Transformers Apache-2.0, PyTorch BSD-3-Clause, SentencePiece Apache-2.0. |
| Baholangan TTS | Navoiy TTS | Apache-2.0 checkpoint 1,88 GiB. CosyVoice2 0.5B bazasi ham Apache-2.0. Alohida CosyVoice2 runtime, mos og‘irliklar va reference ovoz talab qilinadi. Bu Mac’da Navoiy inferensi o‘lchanmagan. |

Qwen3 4B va NavAI Small 16 GB umumiy xotirali Apple M1 Pro uchun tanlangan. STT GPU ishlatganda Metal umumiy xotiradan foydalanadi. Muqobil Whisper modeli tanlanganda u so‘rov uchun alohida yuklanadi. Kundalik model Whisper serverida xotirada qoladi.

Model kartalari: [NavAI Small](https://huggingface.co/navai-uz/whisper-small-uzbek), [Kotib](https://huggingface.co/Kotib/uzbek_stt_v1), [Gearnode](https://huggingface.co/Gearnode/qwen3-asr-uzbek-v2), [Navoiy](https://huggingface.co/aisha-org/navoiy-tts), [CosyVoice2](https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B), [SpeechT5 Uzbek](https://huggingface.co/AbrorBalxiyev/uzbek-tts-model), [HiFi-GAN](https://huggingface.co/microsoft/speecht5_hifigan), [Qwen3 4B](https://huggingface.co/Qwen/Qwen3-4B). FFmpeg litsenziyasini o‘rnatilgan build uchun `ffmpeg -L` bilan ko‘ring.

## Bir martalik o‘rnatish

Loyiha katalogida, PostgreSQL, Redis va Ollama o‘rnatilgan muhitda:

```sh
brew install whisper-cpp ffmpeg espeak-ng
sh infrastructure/scripts/setup.sh
.venv/bin/pip install -r infrastructure/requirements-voice-tools.txt
.venv/bin/python infrastructure/scripts/setup-voice-model.py small
.venv/bin/python infrastructure/scripts/setup-voice-model.py tiny
.venv/bin/python infrastructure/scripts/setup-voice-model.py kotib
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

`.env` faylida sozlang:

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen3:4b
VOICE_LOCAL_ONLY=true
VOICE_STT_URL=http://127.0.0.1:8178
VOICE_STT_MODEL=small
VOICE_STT_DEVICE=auto
VOICE_TTS_ENGINE=espeak
VOICE_TTS_URL=
VOICE_TTS_SPEED=155
```

SpeechT5 kerak bo‘lsa, alohida Python muhiti yarating va og‘irliklarni yuklang:

```sh
.venv/bin/python -m venv .runtime/venv-tts
.runtime/venv-tts/bin/pip install -r infrastructure/requirements-local-tts.txt
.venv/bin/python infrastructure/scripts/setup-voice-model.py speecht5
.runtime/venv-tts/bin/python infrastructure/scripts/local-tts.py --device cpu
```

Backend uchun `VOICE_TTS_ENGINE=speecht5` va `VOICE_TTS_URL=http://127.0.0.1:8181` sozlang. Ovoz sahifasidan SpeechT5 yoki eSpeak ovozini tanlash mumkin. `--device mps` Metal’ni tanlaydi, mos kelmasa `--device cpu` bilan qayta ishga tushiring.

## Ishga tushirish va to‘xtatish

Ollama ochiq bo‘lsa, ikkinchi nusxasini ishga tushirmang. Har bir buyruqni alohida terminalda bajaring:

```sh
ollama serve
sh infrastructure/scripts/voice.sh
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8010
npm run dev
.venv/bin/celery --workdir backend -A app.tasks.worker.celery worker --loglevel=info
```

Har bir xizmatni o‘z terminalida `Ctrl+C` bilan to‘xtating. STT’ni CPU rejimida boshlash uchun `JARVIS_WHISPER_DEVICE=cpu sh infrastructure/scripts/voice.sh` va `.env`da `VOICE_STT_DEVICE=cpu` ishlating. Asosiy model o‘zgarsa, `JARVIS_WHISPER_MODEL`ni tegishli GGML fayliga va `VOICE_STT_MODEL`ni shu model identifikatoriga sozlang.

```sh
curl -f http://127.0.0.1:8010/ready
curl -f http://127.0.0.1:8178/health
curl -f http://127.0.0.1:8181/health  # SpeechT5 ishlatilsa
ollama list
```

## Ovoz va maxfiylik

Ovozli yordamchida mikrofonga ruxsat bering yoki mahalliy audio faylni tanlang. Brauzer mikrofonning shovqinini va aks-sadosini kamaytiradi, FFmpeg ovozni filtrlab 16 kHz mono WAV’ga aylantiradi. Deyarli jim audio bekor qilinadi. Eshitilgan matnni tahrirlab tasdiqlash mumkin. Latin va kirill matni saqlanadi. Normalizator apostrof variantlari va bo‘shliqlarni standartlashtiradi, sheva so‘zlarini taxmin bilan almashtirmaydi.

Mahalliy rejim audio, sintez va Ollama uchun loopback manzillarini tekshiradi. Ovozli suhbat avtomatik veb-qidiruvga so‘rov yubormaydi. Siz ochiq buyurgan YouTube amali saytga ulanishi mumkin. Matnli veb-qidiruv alohida ishlaydi. Audio vaqtinchalik ishlovdan keyin o‘chiriladi. Tasdiqlangan matn va javob suhbat tarixida saqlanadi.

## Sheva sinovi

```sh
.venv/bin/python infrastructure/scripts/voice-eval.py \
  --audio /path/to/consented-audio.wav --region samarqand --style aralash \
  --models tiny small kotib --output .runtime/voice-eval/samarqand.jsonl
```

Audio argumentisiz macOS mikrofonidan yozadi. `--microphone 0 --seconds 12` orqali qurilma indeksi va vaqtni sozlang. To‘g‘ri matnni so‘ralganda kiriting. Hisobotda WER, CER va modelni yuklash bilan birga ketgan vaqt yoziladi. `--save-text` qo‘shilsa, matnlar ham mahalliy faylga yoziladi. Sinov audiosi saqlanmaydi va yuklanmaydi. Har bir hudud uchun bir nechta rozilik olingan yozuv, tez va sekin nutq hamda aralash tilli gaplar bilan solishtiring.

## Ushbu Mac’dagi sinov

13,68 soniyalik ommaviy Uzbek FLEURS namunasida, Metal avtomatik rejimida:

| Model | WER | CER | Yuklash va transkripsiya |
| --- | ---: | ---: | ---: |
| NavAI Tiny | 6,25% | 0,71% | 0,73 s |
| NavAI Small | 0% | 0% | 1,00 s |
| Kotib Medium | 0% | 0% | 2,65 s |

Small shu namunada tezroq bo‘lgani uchun standart tanlov. Bir namuna orqali shevalar, shovqin yoki aralash nutq bo‘yicha umumiy aniqlikni baholab bo‘lmaydi. SpeechT5 CPU’da 5,79 soniyalik WAV chiqardi. Birinchi yuklash bilan 19,61 s, yuklangan serverda qisqa jumla uchun 0,64 s o‘lchandi. Testda ism va vaqt talaffuzida xatolar kuzatildi. eSpeak menyuda alohida tanlanadi.

Sardor va Madinani qaytarish uchun `VOICE_TTS_ENGINE=edge`, `VOICE_TTS_URL=` va `VOICE_ALLOW_EDGE_TTS=true` sozlang. Edge TTS javob matnini Microsoft xizmatiga yuboradi va internet talab qiladi. STT, Ollama va matnni tasdiqlash mahalliy rejimda qoladi.

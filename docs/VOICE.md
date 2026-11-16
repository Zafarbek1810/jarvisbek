# Mahalliy ovoz

Vebda yozishni boshlash tugmasini bosing, mikrofonga ruxsat bering, gapiring va “Yozishni tugatish” tugmasini bosing. Yozuv eng ko‘pi 60 soniya. Tanilgan matn darhol ko‘rinadi, Qwen javobi oqim bilan chiqadi, keyin ovozda o‘qiladi. Keyingi savollar bir suhbat ichida davom etadi. Javob yonidagi “Qayta eshitish” tugmasi brauzer avtomatik ijroni to‘sganda ham ishlaydi. Sahifadan chiqish mikrofonni o‘chiradi va tugallanmagan yozuvni yubormaydi.

## macOS mahalliy sozlash

```sh
brew install whisper-cpp ffmpeg espeak-ng
.venv/bin/pip install -r infrastructure/requirements-voice-tools.txt
.venv/bin/python infrastructure/scripts/setup-voice-model.py
./infrastructure/scripts/voice.sh
```

NavAI o‘zbekchaga maxsus moslangan Whisper tiny og‘irliklari taxminan 151 MB; mahalliy FP16 model taxminan 78 MB. Yuklash faqat o‘rnatish paytida; audio transkripsiya uchun tashqi xizmatga yuborilmaydi. Server faqat `127.0.0.1:8178` da tinglaydi. `.env` ga quyidagilarni kiriting va backendni qayta ishga tushiring:

```dotenv
VOICE_STT_URL=http://127.0.0.1:8178
VOICE_TTS_ENGINE=espeak
VOICE_TTS_URL=
```

Whisper, backend va veb ilova alohida ishlashi kerak. `JARVIS_WHISPER_MODEL` orqali boshqa ko‘p tilli GGML modelini tanlash mumkin. O‘zbekchaga moslanmagan oddiy Whisper small sinovda ko‘p xato qildi; shu sabab standart sifatida NavAI Uzbek tiny tanlandi. Bu model ham xato qilishi mumkin; katta model ko‘proq xotira va vaqt talab qiladi. eSpeak NG `uz` ovozi bor, ammo talaffuzi sun’iy va robotga o‘xshaydi. Tabiiy ovoz sifati kafolatlanmaydi. `uzbek_verified=false` foydalanuvchi nutqi va talaffuz sifati alohida baholanmaganini bildiradi.

## Formatlar va xavfsizlik

Backend brauzer WebM/MP4/Ogg va mobil M4A fayllarini FFmpeg orqali 16 kHz mono PCM WAV ga aylantirib, Whisper `POST /inference` ga `language=uz` bilan yuboradi. Fayl 10 MB bilan cheklangan. Vaqtinchalik audio ish tugagach o‘chiriladi. Konvertatsiya va eSpeak jarayonlari qat’iy argumentlar bilan, shell ishlatmasdan bajariladi; vaqt chegarasi tugasa jarayon o‘ldiriladi. Foydalanuvchi matni eSpeak’ka stdin orqali beriladi. Tashqi Whisper adapteri ham WAV qabul qilishi va `GET /health` da muvaffaqiyatli holat qaytarishi kerak.

`VOICE_TTS_URL` sozlansa, mahalliy eSpeak o‘rniga `POST /synthesize` orqali `{"text":"...","language":"uz"}` qabul qilib WAV qaytaradigan adapter ishlatiladi. `VOICE_TTS_ENGINE=disabled` va bo‘sh URL ovoz chiqarishni o‘chiradi. Brauzerning bulutli SpeechRecognition xizmati ishlatilmaydi.

Transkripsiya va AI javoblari suhbat bazasida saqlanadi. Vebdagi ovoz ijrosi va ovozli tarix joriy sahifa seansida mavjud; asl audio bazaga saqlanmaydi. Mobil yozuv transkripsiyani matnli suhbatga uzatadi; native javobni ovozda o‘qish hali yo‘q.

Manbalar: [whisper.cpp](https://github.com/ggml-org/whisper.cpp), [NavAI Uzbek model](https://huggingface.co/navai-uz/whisper-tiny-uzbek), [eSpeak NG o‘zbekcha ovozi](https://github.com/espeak-ng/espeak-ng/blob/master/docs/languages.md). Model va vositalarning litsenziyalarini tarqatishdan oldin tekshiring.

## Azure Speech ovozlari

Azure portalida Speech resursining **Keys and Endpoint** bo‘limidan kalit va hududni oling. Mahalliy `.env` faylida quyidagilarni sozlang:

```dotenv
VOICE_TTS_ENGINE=azure
VOICE_TTS_URL=
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
```

Backendni qayta ishga tushiring. **Ovozli yordamchi → Javob ovozi** orqali Sardor yoki Madinani tanlang. Standart ovoz — Sardor. Azure’ga sintez uchun javob matni yuboriladi. Mikrofon yozuvi mahalliy Whisper orqali qayta ishlanadi.

## Edge TTS ovozlari

Mahalliy Python muhitiga `.venv/bin/pip install -r infrastructure/requirements-edge-tts.txt` orqali paketni o‘rnating. `.env` faylida `VOICE_TTS_ENGINE=edge` va `VOICE_TTS_URL=` ni sozlab, backendni qayta ishga tushiring. **Ovozli yordamchi → Javob ovozi** orqali Sardor yoki Madinani tanlang.

Bu rejimga Azure obunasi va API kaliti kerak emas. Internet orqali javob matni Microsoft Edge ovoz xizmatiga yuboriladi. Bu norasmiy integratsiya.

## Uzbek Whisper Small

```sh
.venv/bin/python infrastructure/scripts/setup-voice-model.py small
sh infrastructure/scripts/voice.sh
```

`voice.sh` avval NavAI Uzbek Whisper Small modelini ishlatadi. Small fayli bo‘lmasa, NavAI Uzbek Tiny yuklanadi. Tiny’ni qo‘lda tanlash uchun `JARVIS_WHISPER_MODEL=.runtime/models/ggml-tiny-uzbek.bin sh infrastructure/scripts/voice.sh` buyrug‘ini ishlating.

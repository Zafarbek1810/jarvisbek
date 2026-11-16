# Tekshiruv hisoboti

**2026-11-08 · Asia/Samarkand**

| Tekshiruv | Natija |
|---|---|
| Backend unit/API/security/provider | **20 test o‘tdi**, Python 3.12.16; 1 upstream httpx/TestClient deprecation warning |
| Backend dependency resolution | `pip check`: muammo yo‘q |
| Backend dependency audit | **0 ma’lum zaiflik**; [JSON](audits/backend.json) |
| Native PostgreSQL migratsiyasi | Alembic upgrade va `check` o‘tdi; yangi drift yo‘q |
| SQLite migratsiyasi | Birinchi schema uchun upgrade/downgrade/upgrade o‘tdi; SQLite faqat testlarga |
| pgvector | Extension o‘rnatildi; cosine SQL va HNSW index migration o‘tdi |
| Real API smoke | Health/readiness, registration, persistence, owner isolation, memory text search, Ollama status, missing-model stream error o‘tdi |
| Refresh concurrency | Bir tokenni ikki parallel so‘rovda: biri 200, biri 401 |
| Redis/Celery | Haqiqiy memory job navbatdan olindi va bajarildi; model yo‘qligi to‘g‘ri `false` qaytardi |
| Web/mobile TypeScript | O‘tdi |
| Web lint | Xatosiz o‘tdi |
| JS testlar | **8 test o‘tdi**: stream UTF-8, session refresh/retry/error, button, 2 mobile screen flow |
| Web production build | **Next.js 16.4.5 standalone build o‘tdi**; standalone server ishga tushdi, HTTP 200 |
| Browser | Ro‘yxatdan o‘tish, haqiqiy dashboard, task create/complete/filter va delete-confirm cancel va logout tekshirildi |
| Expo config | SDK 58 konfiguratsiyasi o‘tdi |
| iOS JS bundle | **O‘tdi**, 1165 module, Hermes taxminan 2.6 MB |
| Android JS bundle | **O‘tdi**, 1159 module, Hermes taxminan 2.5 MB |
| JS dependency audit | **12 moderate**, **0 high/critical**; [JSON](audits/javascript.json) |
| Docker | YAML/services/healthcheck tuzilishi tekshirildi; Docker CLI yo‘q, image build/runtime **sinalmagan** |
| Native mobile runtime | `xcrun simctl` mavjud emas; telefon/simulator’da ishga tushirish **sinalmagan** |
| Ovoz | Veb Whisper Uzbek tiny + eSpeak ulangan. Ochiq inson ovozi, WebM/M4A va audio javob sinaldi; talaffuz sifati cheklangan. Quyidagi yakuniy ovoz natijalariga qarang. |
| Haqiqiy Qwen chat/embedding | Qwen3 8B bilan haqiqiy provider va JARVIS streaming sinovi o‘tdi; embedding modeli hali sinalmagan |

## Aniq chegaralar

Mock javoblar har doim `[SINOV JAVOBI]` belgisi bilan. Provider testlari HTTP MockTransport ishlatadi; ular haqiqiy model sifati yoki tezligini tasdiqlamaydi. Settings persistence va fallback tanlash simulyatsiyada tekshirildi, haqiqiy model switching emas. Mobil screen testlari native primitiv mocklari bilan; bundle natijasi imzolangan IPA/APK yoki qurilma runtime testi emas.

JS’dagi qolgan moderate advisories Expo CLI/glob/minimatch va ESLint parser vositalariga tegishli. Patched Next/Expo/Vitest/Zod bilan high/critical topilmadi. Npm scoped override urinishlarida mavjud transitive lock versiyalarini saqladi; samarasiz overrides olib tashlandi. `npm audit fix --force` bilan mos kelmaydigan framework downgrade qilinmadi. Qolgan findinglar yashirilmagan.

Disposable QA hisoblari va yozuvlari tekshiruvdan keyin olib tashlandi. `screenshots/tasks.png` test paytidagi haqiqiy web UI dalili. Production ma’lumotlar bazasi yoki tashqi hisoblar o‘zgartirilmadi. Ollama modeli yuklanmadi.

## Qayta tekshirish

```sh
.venv/bin/pytest backend/tests -q
.venv/bin/pip check
.venv/bin/alembic -c backend/alembic.ini check
npm run typecheck
npm run lint
npm test
npm run build
npm run config -w apps/mobile
EXPO_OFFLINE=1 npm exec -w apps/mobile -- expo export --platform ios --output-dir dist
EXPO_OFFLINE=1 npm exec -w apps/mobile -- expo export --platform android --output-dir dist-android
npm audit
# Backend va lokal xizmatlar ishlaganda; faqat QA hisoblari yaratiladi va tozalanadi:
PYTHONPATH=backend .venv/bin/python infrastructure/scripts/smoke.py
```

Tekshiruvdan so‘ng web/API preview serverlari va Celery worker to‘xtatildi. PostgreSQL/Redis lokal xizmatlari saqlandi. Qayta ishga tushirish buyruqlari README’da.

## Qwen3 8B bilan haqiqiy sinov — 2026-11-08

- `qwen3:8b` o‘rnatilgani Ollama `/api/tags` orqali tasdiqlandi (Q4_K_M, 8.2B). 4B hali o‘rnatilgan modellar ro‘yxatida yo‘q edi. Yuklashga tegilmadi.
- Native provider, temperature=0.2: `2 + 2 = 4` va JARVIS tanishuvi, 3.2 soniya.
- FastAPI autentifikatsiyasi va `/chat/stream` orqali haqiqiy model javobi: `Salom! 2 + 2 = 4.` Oqim `done` bilan tugadi, 13.7 soniya. Vaqtinchalik QA hisobi tozalandi.
- `ollama ps`: 100% GPU, taxminan 5.6 GB, kontekst 4096.
- Birinchi `/no_think` tanishuv sinovida mazmunsiz o‘zbekcha matn chiqdi. Keyingi odatiy rejimdagi sodda savollar to‘g‘ri bo‘ldi. Bu sinov o‘zbekcha umumiy javob sifatini to‘liq tasdiqlamaydi.
- Backend 8010 va web 3010 foydalanuvchi so‘roviga binoan qayta ishga tushirildi va ishlayotgan holatda qoldirildi.

## Qwen3 javob kechikishi — 2026-11-08

Ollama `/api/show` Qwen3 8B uchun `thinking.default=true` ekanini ko‘rsatdi. Oldingi provider bu qiymatni o‘zgartirmagan, UI esa faqat yakuniy content’ni ko‘rsatgan. Standart testda prompt evaluation 1.822 s va generation 9.412 s bo‘ldi; wall time 37.068 s bo‘lgani sababli qo‘shimcha kutish/navbat ham bo‘lishi mumkin. Uni faqat thinking vaqti deb hisoblab bo‘lmaydi.

`think=false`, 15 daqiqa keep-alive va indekslangan xotira bo‘lmaganda embedding chaqirmaslik qo‘shildi. Qwen3’dan boshqa modellarning thinking default’i o‘zgartirilmaydi. Har foydalanuvchi Sozlamalarda chuqur tahlilni qayta yoqishi mumkin; murakkab savollarda fikrlash sifati va tezlik o‘rtasida murosa bor.

Haqiqiy JARVIS API sinovi (model xotirada):
- Birinchi matn: 2.036 s; to‘liq javob: 2.667 s.
- Birinchi matn: 0.211 s; to‘liq javob: 1.389 s.

Natijalar qisqa savollar uchundir. Sovuq yuklash, uzun tarix, uzun javob va parallel so‘rovlar sekinroq bo‘lishi mumkin. 23 backend va 8 JS testi, typecheck/lint/build o‘tdi. Xotira bo‘sh bo‘lganda embedding chaqirilmasligi haqiqiy PostgreSQL’da tekshirildi. Uzbek ifodalash sifati hali mukammal emas. QA hisobi tozalandi; backend/web foydalanuvchi uchun ishlayotgan holatda qoldirildi.

## Ovozli suhbat ulanishi — 2026-11-08

- whisper.cpp 1.9.5, FFmpeg 9.0.2 va eSpeak NG 1.52.0 o‘rnatildi. `small-q5_1` 190 MB modelining SHA256 qiymati rasmiy model metama’lumoti bilan tekshirildi.
- Veb MediaRecorder → WebM/M4A → autentifikatsiyalangan API → FFmpeg PCM WAV → Whisper → Qwen → eSpeak Uzbek WAV yo‘li tekshirildi. Sun’iy namuna transkripsiyasi 0,58–0,94 s, Qwen javobi sovuq so‘rovda 14,09 s bo‘ldi; bu inson ovozi uchun tezlik kafolati emas.
- Muhim sifat cheklovi: eSpeak yaratgan “Salom Jarvis. Ikki qo‘shuv ikki necha bo‘ladi?” jumlasi Whisper small tomonidan buzib tanildi. Texnik zanjir muvaffaqiyati o‘zbekcha nutq aniqligi degani emas. `uzbek_verified=false` saqlanadi; sun’iy talaffuz tabiiy ovozga tenglashtirilmaydi.
- 28 backend testi; 11 JS testi; veb TypeScript, ESLint va production build o‘tdi. Ovoz testlari: codec MIME, WebM/M4A normalizatsiya, bo‘sh audio, adapter xatosi, process timeout kill/reap, service health, mikrofon ruxsati rad etilishi, transkripsiya/javob/ijro va navigatsiyada yozuv bekor qilinishi.
- Sinov uchun faqat vaqtinchalik QA hisob yaratildi va o‘chirildi; foydalanuvchi mikrofoni avtomatik yozilmadi. Real native mobil TTS ijrosi sinovdan o‘tmagan.
- Qayta tekshirish: `PYTHONPATH=backend .venv/bin/python infrastructure/scripts/voice-smoke.py` (Whisper/backend/Qwen/eSpeak ishga tushgan bo‘lishi kerak). Natija `.runtime/voice-smoke.json` ga yoziladi; audio sifati uchun inson bahosi kerak.

### Yakuniy model almashtirildi

Oddiy Whisper small o‘rniga **NavAI `whisper-tiny-uzbek`** yuklandi (151 MB safetensors; SHA256 `95102b41a7e84ced74f1e640ad3ca00fc6c48b96419642345de3b0bd829936c8`). Faqat tensorlar yuklandi; tashqi Python kod bajarilmadi. Whisper.cpp GGML FP16 ga konvertatsiya qilingan model 77 691 730 bayt, Apple Metal’da to‘g‘ri yuklandi.

[Google FLEURS Uzbek test](https://huggingface.co/datasets/google/fleurs) dan `10014255987590674947.wav` — 13,68 soniyalik ochiq inson nutqi bilan taqqoslandi. Oddiy small matnni ancha buzdi; o‘zbekchaga moslangan tiny esa 0,61 soniyada tinish belgilaridan tashqari faqat “ularning” o‘rniga “bularning” deb yozdi. Bu bitta namuna; umumiy aniqlik yoki foydalanuvchi talaffuziga kafolat emas. Natija `.runtime/voice-human-uzbek-model.json` da. Shu sabab yakuniy standart model NavAI Uzbek tiny. Model manbasi va litsenziyasi: https://huggingface.co/navai-uz/whisper-tiny-uzbek .

Yakuniy autentifikatsiyalangan API sinovi inson ovozi bilan takrorlandi: WebM 0,24 s, M4A 0,23 s transkripsiya; uzun Qwen javobi 10,05 s, 1 644 734 bayt WAV javob yaratildi. WebM matnida bitta, M4A matnida ikkita so‘z farqi bor edi; tinish belgilari chiqarilmaydi. Ovoz yaratish sifati robotga o‘xshashligicha qoladi. Backend 8010, veb 3010 va Whisper 8178 da ishga tushirilgan holda qoldirildi. Ishlatilmaydigan umumiy Whisper small modeli olib tashlandi.

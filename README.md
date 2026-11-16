# JARVIS — o‘zbekcha shaxsiy AI yordamchi

Mahalliy Ollama uchun Next.js + FastAPI + Expo monorepo. OpenAI API ishlatilmaydi. AI modellar avtomatik yuklanmaydi.

## Tez boshlash

Kerak: Node 22+, Python 3.12+, PostgreSQL 14+ va pgvector, Redis, Ollama. Tavsiya: Docker Desktop; AI tezligi uchun Ollama macOS’da native ishlasin.

```sh
./infrastructure/scripts/setup.sh
# .env ichidagi manzillarni tekshiring
# Docker bilan: (Docker Desktop ishga tushgan bo‘lsin)
docker compose up --build
```

Veb: http://localhost:3010 · API: http://localhost:8010/docs . Ilovada avval o‘z hisobingizni yarating. Tayyor umumiy parol yoki avtomatik demo foydalanuvchi yo‘q.

## Native ishlab chiqish

PostgreSQL’da `jarvis` foydalanuvchisi/bazasi va `vector` extension mavjud bo‘lsin. Migratsiya foydalanuvchisiga birinchi marta extension yaratish ruxsati kerak (yoki DBA oldindan yaratsin). `.env` ichida `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` ni sozlang.

```sh
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8010
# Ikkinchi terminal:
npm run dev
# Uchinchi terminal (fon indekslash):
.venv/bin/celery --workdir backend -A app.tasks.worker.celery worker --loglevel=info
```

Veb API manzili o‘zgarsa `apps/web/.env.local` ga `NEXT_PUBLIC_API_URL=http://localhost:8010/api/v1` kiriting va Next.js’ni qayta ishga tushiring. Compose uchun shu manzil build argument sifatida olinadi; bu Docker ichki hostname’i emas, brauzer kira oladigan manzil bo‘lishi kerak.

Ushbu ish sessiyasida alohida PostgreSQL `.runtime/postgres` katalogida **5433**, Redis **6380** portida sozlanadi. `.env.example` standart Docker/local portlarini saqlaydi. Mavjud boshqa bazalar o‘zgartirilmaydi. Klaster qayta ishga tushirish:

```sh
pg_ctl -D .runtime/postgres -l .runtime/postgres.log -o '-h 127.0.0.1 -p 5433 -k /private/tmp' start
redis-server --bind 127.0.0.1 --port 6380 --dir "$PWD/.runtime" --appendonly yes
```

Bu development klasteri faqat loopback manzilida trust autentifikatsiyasi bilan ishlaydi. Uni tashqi tarmoqqa ochmang. Production’da alohida hisob/parol, HTTPS, migratsiya roli va zaxira nusxa siyosatini sozlang.

## Ollama va modellar

macOS o‘rnatish: https://ollama.com/download yoki `brew install --cask ollama`. Ilovani oching yoki `ollama serve` buyrug‘ini bajaring. Katta yuklamalarni boshlash uchun quyidagi buyruqlarni o‘zingiz bajaring:

```sh
ollama pull qwen3:8b
ollama pull qwen3:4b
ollama pull nomic-embed-text
ollama list
```

`AI_PROVIDER=ollama` odatiy. `OLLAMA_BASE_URL=http://localhost:11434` native backend uchun. Docker ichidan `http://host.docker.internal:11434`. Ollama faqat loopback tinglasa va konteyner ulanmasa, Ollama’ning host binding sozlamasini tekshiring; tashqi kirishni firewall bilan cheklang. Qwen3 8B yetarli tezkor xotira talab qiladi. Model yo‘qligi va xotira xatolari foydalanuvchiga ochiq ko‘rsatiladi.

Modelni o‘zgartirish: **Sozlamalar → O‘rnatilgan model → Saqlash**. Faqat Ollama ro‘yxatidagi model qabul qilinadi; hech narsa yuklanmaydi. Standart primary model topilmay, o‘rnatilgan 4B fallback mavjud bo‘lsa, orkestrator yengil modelni tanlaydi. Xotira yetishmasligida avtomatik qayta generatsiya qilinmaydi — kichik modelni qo‘lda tanlang. `.env` dagi model o‘zgarsa backendni qayta ishga tushiring. Prompt backend `backend/app/core/uzbek_prompt.txt` da; foydalanuvchi qo‘shimcha ko‘rsatma saqlashi mumkin.

## Aniq belgilangan sinov rejimi

```sh
AI_PROVIDER=mock .venv/bin/uvicorn app.main:app --app-dir backend --port 8010
```

Bu haqiqiy AI emas; har javob `[SINOV JAVOBI]` bilan boshlanadi. Xotira semantik vektorlari yaratilmaydi. Ma’lumotlar va autentifikatsiya haqiqiy bazada ishlaydi.

## Mobil dastur

```sh
# apps/mobile/.env faylida kompyuterning haqiqiy LAN IP manzilini kiriting (ushbu muhitda avtomatik sozlandi):
# EXPO_PUBLIC_API_URL=http://192.168.1.25:8010/api/v1
npm run start -w apps/mobile
```

Telefon va kompyuter bitta tarmoqda bo‘lsin. Backend `0.0.0.0` da tinglasin, firewall 8010-portga ruxsat bersin. Jismoniy telefonda `localhost` ishlamaydi. Expo SDK 58 bilan mos Expo Go yoki development build kerak. SecureStore refresh tokenni saqlaydi; access token xotirada. Mobil chat NDJSON’ni to‘liq olgach ko‘rsatadi; veb tokenlarni oqimda chiqaradi. Mikrofon faqat ruxsat va aniq tugma bilan yoqiladi.

## Imkoniyatlar

- Hisob yaratish/kirish/chiqish, Argon2, JWT, bir martalik refresh tokenlar, foydalanuvchi izolyatsiyasi.
- Suhbat tarixi, NDJSON streaming, Markdown/kod bloklari, nusxalash va qayta so‘rov, o‘zbekcha system prompt.
- Xotira CRUD, teg/kategoriya, chatda ishlatish ruxsati, audit tarixi, Ollama embedding va pgvector qidiruv; model bo‘lmasa matnli qidiruv.
- Vazifalar CRUD, muhimlik, muddat, faol/bajarilgan filtr; loyihalar, texnologiyalar, havolalar va API qaydlari.
- Bilim qaydlari/havolalar, TXT/MD/PDF matn ajratish, hajm/tur tekshiruvi, qidiruv, AI xulosa, Celery orqali semantik indekslash.
- Daromad, xarajat, g‘oya va KPI yozuvlari; UZS/USD alohida deterministik hisob-kitob; API orqali AI izoh.
- Sxemali va auditli 10 ichki AI vositasi. Yozish amallari chatda foydalanuvchining aniq ruxsatini talab qiladi. Arbitrary shell/kod bajarish yo‘q.
- Qorong‘i/yorug‘ mavzu va moslashuvchan o‘zbekcha veb UI; Expo asosiy ekranlari.

## Ovoz, integratsiyalar va cheklovlar

[Ovoz sozlamalari](docs/VOICE.md), [arxitektura va xavfsizlik](docs/ARCHITECTURE.md), [bosqichlar](IMPLEMENTATION_PLAN.md), [tekshiruv natijalari](docs/VERIFICATION.md).

Veb ovozli suhbat mahalliy Whisper va eSpeak NG bilan ishlaydi: yozish → WAV konvertatsiya → matn → Qwen javobi → ovoz. Sozlash va ishga tushirish buyruqlari [ovoz hujjatida](docs/VOICE.md). Model repo ichiga kiritilmagan. O‘zbekcha tanish xato qilishi mumkin; eSpeak ovozi robotga o‘xshaydi. Ovoz sozlanmasa matnli yordamchi ishlaydi. GitHub/Calendar/email/Telegram/Notion ulanmagan. Esdalik scheduler’i, OCR/DOCX, offline mobil sinxronizatsiya, native desktop qadoq va production sertifikatsiyasi hali yo‘q. Haqiqiy model va qurilmalar sinovi talab qilinadi.

## Tekshiruv

```sh
.venv/bin/pytest backend/tests -q
npm run typecheck
npm run lint
npm test
npm run build
npm run config -w apps/mobile
# Ma’lumotlar xizmatlari:
curl http://localhost:8010/health
curl http://localhost:8010/ready
```

Testlar uchun SQLite ajratilgan bazasi ishlatiladi; haqiqiy PostgreSQL migratsiyasi alohida tekshiriladi. `docker compose down` ma’lumotlarni saqlaydi; `down -v` bazani o‘chiradi. Ishlab chiqarishda `ENVIRONMENT=production`, `COOKIE_SECURE=true`, kuchli maxfiy kalit, HTTPS va aniq `CORS_ORIGINS` zarur. Redis ishlamasa production so‘rovlari himoya uchun 503 oladi.

API bo‘yicha asosiy manbalar: [Ollama](https://docs.ollama.com/api/chat), [FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/quickstart.html), [Next.js](https://nextjs.org/docs/app/getting-started/installation), [Expo](https://docs.expo.dev/router/introduction/), [pgvector](https://github.com/pgvector/pgvector).

## Javob tezligi

Qwen3 uchun `OLLAMA_THINK=false` odatiy tezkor rejim. Sozlamalar → Chuqur tahlil orqali murakkab savollar uchun yoqish mumkin; bu javobni sekinlashtiradi. `OLLAMA_KEEP_ALIVE=15m` modelni GPU xotirasida uzoqroq ushlab turadi va taxminan model hajmicha xotira band bo‘lib turadi. Qisqa savollarning real API testida 1.4–2.7 s o‘lchandi; bu barcha savollar uchun kafolat emas. Model yuklash, uzun kontekst va navbat kutish vaqtini oshiradi.

## Veb-qidiruv

Chatga `/search <so‘rov>` yozing, masalan `/search Samarqand bugungi yangiliklari`. Jarvis qidiruv natijalaridan Qwen orqali javob tayyorlaydi va manba havolalarini qo‘shadi. Qidiruv uchun internet kerak. Faqat `/search` dan keyingi matn tashqi qidiruv xizmatiga yuboriladi.

Yangilik va ob-havo savollarida Jarvis avtomatik qidiradi. Ob-havo uchun shaharni ayting, masalan, «Samarqandda bugun ob-havo qanday?».

macOS’da `DESKTOP_VOICE_COMMANDS=true` bilan localhost’dagi **Ovozli yordamchi** kompyuter buyruqlarini bajaradi. Masalan, «Google Chrome dasturini och», «Ovozni pasaytir» yoki «YouTube’da o‘zbekcha jazz qo‘y». YouTube videosi brauzerda ochiladi, avtomatik ijro brauzer sozlamalariga bog‘liq.

## Mahalliy MCP server

```sh
.venv/bin/pip install -r infrastructure/requirements-mcp.txt
sh infrastructure/scripts/mcp.sh
```

Server stdio orqali ishlaydi. MCP klientida `.mcp.json` faylidagi `jarvis-local` yozuvini ishlating. Boshqa kompyuterda skriptning mutlaq yo‘lini moslang. Vositalar `web_search`, `speech_status` va `run_desktop_command`. macOS buyruqlari development rejimida `DESKTOP_VOICE_COMMANDS=true` bo‘lganda ishlaydi.

YouTube buyrug‘i video havolasini topishi uchun `.venv/bin/pip install -r infrastructure/requirements-youtube.txt` buyrug‘ini bajaring. Jarvis YouTube orqali video ID qidiradi. Video topilmasa, qidiruv sahifasini ochadi.

Oflayn o‘zbekcha ovoz rejimi, modellar va sheva sinovlari uchun [mahalliy ovoz qo‘llanmasi](docs/LOCAL_VOICE.md)ni ko‘ring.

## Telegram

Telegram’dagi [BotFather](https://t.me/BotFather) orqali `/newbot` bilan bot yarating. Tokenni loyihaning mahalliy `.env` faylidagi `TELEGRAM_BOT_TOKEN`ga yozing va backendni qayta ishga tushiring. Tokenni chatga yoki repozitoriyga qo‘ymang.

Redis, Ollama va Jarvis ishlayotganida alohida terminalda:

```sh
PYTHONPATH=backend .venv/bin/python -m app.providers.telegram
```

**Integratsiyalar → Telegram’ni ulash → Telegram’da ochish** orqali botda **Start** bosing. Havola bir martalik va 10 daqiqa amal qiladi. Bot faqat bog‘langan shaxsiy chatdagi matnga mahalliy Ollama orqali javob beradi. Telegram xabar va javoblarni o‘z serverlari orqali uzatadi. Jarayon long polling ishlatadi, shuning uchun ochiq port yoki webhook kerak emas. Bot uchun boshqa polling jarayoni yoki webhook faol bo‘lsa, avval uni to‘xtating.

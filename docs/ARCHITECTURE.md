# Arxitektura

Next.js App Router (TypeScript) va Expo Router mijozlari faqat FastAPI `/api/v1` bilan aloqa qiladi. Ollama native `/api/chat`, `/api/embed`, `/api/tags`, `/api/version` endpointlari faqat backendda chaqiriladi. OpenAI yoki pullik bulut provayderi yo‘q.

SQLAlchemy modellari PostgreSQL uchun mo‘ljallangan; vektorlar pgvector `vector(768)` turida. SQLite faqat izolyatsiyalangan testlar uchun JSON variantidan foydalanadi. Alembic boshlang‘ich sxemani muzlatilgan migratsiya bilan yaratadi. Ishlayotgan backend `create_all` ishlatmaydi.

Har bir yozuv `owner_id` bilan ajratiladi. Suhbat xabarlariga faqat egasi suhbat orqali kira oladi. Loyihaga havola berilgan vazifalarda loyiha egasi tekshiriladi. Refresh tokenlar bazada SHA-256 xeshlanadi, almashtirish atomar va bir martalik; parollar Argon2. Access token 15 daqiqa, refresh token 14 kun. Logout refresh tokenni bekor qiladi; oldingi access token muddati tugaguncha amal qiladi.

Veb token xotirada, refresh HttpOnly/SameSite=Strict cookie’da. Mobil refresh token SecureStore’da. Ishlab chiqarishda `COOKIE_SECURE=true`, HTTPS, aniq CORS manbalari va kuchli `JWT_SECRET` zarur. Himoya middleware’i ishlab chiqarishda Redis yo‘q bo‘lsa so‘rovni rad etadi. Development rejimida bitta jarayon uchun lokal limit mavjud. Reverse proxy’da request hajmini va tezligini ham cheklang; `X-Forwarded-For` mijozdan ishonchli olinmaydi.

Orkestrator faqat cheklangan vositalarni taqdim etadi. Pydantic `extra=forbid`; barcha yozuvchi vositalar shu so‘rovdagi foydalanuvchi ruxsatini talab qiladi. O‘qish vositalari ham egaga tegishli. Shell yoki kod bajarish vositasi mavjud emas. Suhbatda 24 xabar va taxminiy kontekst budjeti bor; tokenizer asosidagi aniq hisob hali yo‘q. Har javobga 4 vosita davri, har davrga 5 amal chegarasi bor. Xotira matni ishonchsiz kontekst sifatida belgilanadi.

Xotira yaratishda mahalliy embedding urinishi qilinadi. Model bo‘lmasa ma’lumot saqlanadi va `indexed=false` qaytariladi. Semantik qidiruv faqat mavjud vektorlar va bir xil embedding modeli bilan, o‘xshashlik chegarasi bilan ishlaydi. Vektor xizmati yo‘q bo‘lsa matn qidiruviga aniq `mode=text` bilan qaytiladi. `use_in_chat=false` xotira AI kontekstiga kirmaydi.

Bilim fayllari diskka bajariladigan shaklda yozilmaydi. TXT/MD UTF-8 va PDF magic-header tekshiriladi, 5 MB/200 bet/1 million belgi chegarasi bor. PDF parsing uchun ishlab chiqarishda alohida izolyatsiyalangan worker va CPU/time limit tavsiya etiladi. OCR, DOCX parser, antivirus va to‘liq revision tarixi hali yakunlanmagan. Matn bo‘laklari saqlanadi; Celery indekslash va pgvector/HNSW hujjat qidiruvi yozilgan. Haqiqiy nomic-embed-text modeli bo‘lmagani sababli semantik natijalar real modelda sinalmagan.

Celery xotirani qayta indekslash vazifasini qo‘llaydi. Avtomatik eslatma scheduler’i hali mavjud emas. Tashqi integratsiyalar faqat rejalashtirilgan sifatida ko‘rsatiladi; hech qanday tashqi hisobga ulanmaydi.

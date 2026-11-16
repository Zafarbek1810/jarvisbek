# API yo‘riqnomasi

Asos: `http://localhost:8010/api/v1`. Interaktiv sxema: `/docs`.

Autentifikatsiya: `POST /auth/register`, `/auth/login`. JSON `email`, `password`; ro‘yxatdan o‘tishda `name`. Veb refresh HttpOnly cookie’da. Mobil `?mobile=true` bilan refresh tokenni olib SecureStore’da saqlaydi. Access token bilan `Authorization: Bearer ...`. `POST /auth/refresh` va `/auth/logout` JSON `{}`; mobilda `{"refresh_token":"..."}`.

CRUD: `GET/POST /tasks`, `/memories`, `/projects`, `/knowledge`, `/business`; `GET/PUT/DELETE /{id}`. PUT to‘liq hujjat sxemasini oladi; noma’lum maydonlar rad etiladi. GET `q`, `limit` (1–100), `offset`, `sort=newest|oldest|title`. Vazifalarda `completed` va `category` filtrlari. Sana ISO `YYYY-MM-DD`.

`GET /memories/search?q=...&semantic=true`, `/knowledge/search`: `mode=semantic|text`. Vektor modeli bo‘lmasa matnli rejim; bu holat javobda aniq belgilanadi. `POST /knowledge/upload` multipart `file`: TXT/MD/PDF, 5 MB. `POST /knowledge/{id}/summarize` AI xulosa. `POST /knowledge/{id}/index` Celery navbatiga vektor yaratish ishini yuboradi; Redis va worker kerak.

`GET /conversations?q=...`, `/conversations/{id}/messages`, `DELETE /conversations/{id}`. `POST /chat/stream`:

```json
{"content":"Bugungi ishlarimni rejalashtiraylik","conversation_id":null,"allowed_tools":[],"regenerate":false}
```

Javob `application/x-ndjson`: har satr bitta JSON. Hodisalar: `start` (`conversation_id`), `delta` (`content`), `tool` (`message`), `done`, `error` (`message`). Streaming boshlangach xatolar HTTP status o‘rniga `error` hodisasi orqali qaytadi. `regenerate=true` mavjud suhbatning eng so‘nggi user xabariga qayta javob oladi. Oldingi assistant javobi almashtiriladi. Bir suhbatga parallel generatsiya yubormang.

Yozuvchi vositalar uchun `allowed_tools`: `save_memory`, `create_task`, `update_task`, `save_notes`. Bu ro‘yxatni mijoz foydalanuvchining aniq ruxsatisiz qo‘shmasin. O‘qish vositalari: `search_memories`, `search_projects`, `search_knowledge`, `summarize_documents`, `generate_reports`, `analyze_code`. Barcha vositalar user ma’lumotlari doirasida ishlaydi.

`GET /ai/status`: provider/connection/models/embedding/settings va qo‘lda o‘rnatish buyruqlari. `PUT /ai/settings`: `model`, `temperature`, `context_length`, `system_prompt`. Faqat o‘rnatilgan model qabul qilinadi.

`GET/PUT /settings` mavzu saqlaydi (`theme=dark|light`). `GET /dashboard` real hisob-kitoblar; `/users/me` profil. `/integrations` hali ulanmagan xizmatlar ro‘yxati.

`GET/POST /projects/{id}/notes`, `DELETE /projects/{id}/notes/{note_id}`. `POST /projects/analyze-code` `{"text":"..."}`. Kod bajarilmaydi. `GET /business/report/summary?currency=UZS&ai=true`: bazadagi haqiqiy yozuvlar hisoboti va ixtiyoriy AI izoh. Valyutalar birlashtirilmaydi.

`GET /voice/status`, `POST /voice/transcribe` (multipart audio), `POST /voice/speak` (`{"text":"..."}`). Ovoz adapterlari sozlanmasa 503. Uzbek sifati tekshirilmagan.

Xato shakli: `{"error":{"message":"O‘zbekcha izoh","fields":["body.title"]}}`. 401 kirish kerak, 404 topilmadi yoki boshqa egaga tegishli, 422 validatsiya, 429 limit, 503 xizmat ulanmagan. `/health` jarayon, `/ready` PostgreSQL/Redis tayyorligi.

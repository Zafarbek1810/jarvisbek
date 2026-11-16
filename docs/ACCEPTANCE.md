# Qabul mezonlari bo‘yicha yakuniy tekshiruv

**2026-11-08**. Raqamli dalillar: [VERIFICATION.md](VERIFICATION.md).

| # | Talab | Holat |
|---|---|---|
| 1 | Backend ishlashi | ✅ Python 3.12/FastAPI native start, health va API smoke |
| 2 | PostgreSQL | ✅ Alohida PostgreSQL 14, 5433-port |
| 3 | Redis | ✅ 6380-port, Celery ulanishi va haqiqiy job |
| 4 | Migratsiyalar | ✅ PostgreSQL upgrade, HNSW indekslar va Alembic drift check |
| 5 | Autentifikatsiya | ✅ API testlari, brauzer signup, parallel refresh |
| 6 | Ollama ulanishi | ✅ Native version/tags endpointlari |
| 7 | Qwen3 chat | ⚠ Model yo‘q; haqiqiy generatsiya sinalmagan |
| 8 | Mock rejim | ✅ `[SINOV JAVOBI]` aniq belgisi bilan |
| 9 | O‘zbek prompt | ✅ Markaziy backend prompt va sozlamalar; ⚠ real modelning tili sinalmagan |
| 10 | Suhbat saqlanishi | ✅ Testlarda user/assistant va regenerate |
| 11 | Xotira | ✅ CRUD/matn/ruxsat/audit; ⚠ haqiqiy embedding modeli yo‘q |
| 12 | Vazifalar | ✅ API va brauzer create/complete/filter |
| 13 | Loyihalar | ✅ CRUD/qayd/kod tahlili; AI natija mock bilan |
| 14 | Bilimlar markazi | ✅ CRUD/fayl validation/qidiruv/mock xulosa; ⚠ real semantik model qolgan |
| 15 | Veb dashboard | ✅ Native backend bilan brauzerda |
| 16 | O‘zbek UI | ✅ Asosiy veb/mobil oqimlar, auth, bo‘sh/error holatlar va hujjatlar |
| 17 | Ovoz | ⚠ Veb mahalliy STT/TTS ulangan; formatlar va audio javob sinaldi. Uzbek tanish/talaffuz sifati cheklangan, mobil TTS hali yo‘q |
| 18 | Mobil ishlashi | ✅ TS/config/2 screen testi/iOS+Android bundle; ⚠ qurilmada runtime sinalmagan |
| 19 | Docker | ✅ Konfiguratsiya va YAML; ⚠ CLI yo‘q, build/runtime sinalmagan |
| 20 | Testlar | ✅ 20 backend + 8 JS; ⚠ model/qurilma/Docker E2E qolgan |
| 21 | Production builds | ✅ Web standalone va mobile JS bundles; ⚠ Docker image va imzolangan native paket yo‘q |
| 22 | Hujjatlar | ✅ README, API, arxitektura, ovoz, xavfsizlik, reja va tekshiruv dalillari |

To‘liq production tayyorligi da’vo qilinmaydi. Model yuklash, real ovoz sifati, native qurilma, Docker runtime, backup/restore va yuklama sinovlari qolgan. JS toolchain’da 12 moderate advisory ochiq, high/critical 0; backend auditida ma’lum zaiflik 0. Desktop native paket va tashqi integratsiyalar yaratilmagan/ulanmagan.

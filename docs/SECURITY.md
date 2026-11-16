# Xavfsizlik tekshiruvi

Bu repo production sertifikatsiyasi yoki mustaqil penetration-testdan o‘tgan deb hisoblanmaydi.

Amalda tekshirilgan chegaralar:

- Begona foydalanuvchining vazifa, loyiha, suhbat va xotirasiga kira olmaslik.
- Vazifaga begona loyiha ID sini bog‘lay olmaslik.
- Noto‘g‘ri/ortiqcha kirish maydonlarini rad etish.
- Bir martalik refresh tokenni qayta ishlatish va parallel almashtirishga qarshi atomar update.
- Parollar Argon2; token xeshlari bazada, ochiq tokenlar logga yozilmaydi.
- JWT faqat HS256, belgilangan issuer/audience va amal muddati bilan tekshiriladi.
- Veb HttpOnly/SameSite cookie; token browser localStorage’da saqlanmaydi.
- Yozuvchi AI vositalari aniq foydalanuvchi ruxsati va Pydantic sxemasidan o‘tadi. Shell ijrosi mavjud emas.
- Chat uchun o‘chirilgan xotiralar vosita qidiruviga ham qo‘shilmaydi.
- Upload turi/hajmi, PDF signature va matn chegaralari tekshiriladi; fayllar bajarilmaydi.
- Production’da HTTPS CORS, secure cookie va tasodifiy kalit talab qilinadi. Redis yo‘q bo‘lsa limiter fail-closed ishlaydi.

Bog‘liqliklar auditidan so‘ng Python 3.12 va patched FastAPI/Starlette/JWT/multipart/anyio paketlariga o‘tildi. JS auditidan so‘ng Next.js, Expo, Vitest va Zod yangilandi. Yakuniy audit natijasi `VERIFICATION.md` da yoziladi; eski natijalar hozirgi paketlar uchun da’vo emas.

Chegaralar: access token logoutdan so‘ng 15 daqiqagacha amal qilishi mumkin; parallel generatsiyani mijoz boshqaradi; PDF CPU/memory izolyatsiyasi alohida worker’da kuchaytirilishi kerak; backup/restore, yuklama, mobil qurilma, Docker runtime va haqiqiy STT/TTS sinovi qolgan. Ovoz xizmatlarini faqat boshqariladigan mahalliy adapterlarga ulang. `.env` repozitoriyga kiritilmasin. Development PostgreSQL/Redis faqat loopback’da; production parollarini almashtiring.

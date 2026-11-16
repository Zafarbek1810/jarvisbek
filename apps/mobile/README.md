# JARVIS mobil

Expo Router va React Native, mahalliy FastAPI bilan. `cp .env.example .env` va haqiqiy LAN IP manzilini yozing. Telefon va backend bitta tarmoqda ishlashi kerak. `npm run start -w apps/mobile` root katalogdan ishga tushadi. Qo‘llanadigan SDK versiyasi `package.json` da aniq ko‘rsatilgan; mos Expo Go/development build kerak.

Native JS bundle tekshiruvi: `EXPO_OFFLINE=1 npm exec -w apps/mobile -- expo export --platform ios --output-dir dist`.

Kirish, bosh sahifa, suhbat, mikrofon adapteri, xotira/vazifa/loyiha CRUD va sozlamalar mavjud. Web’dagi barcha funksiyalar mobilga to‘liq ko‘chirilmagan. Mobil chat javobi to‘liq olinib ko‘rsatiladi. Ovoz ijrosi, fayl yuklash, semantik qidiruv boshqaruvi va offline sinxronizatsiya hali yo‘q. Mikrofon va SecureStore fizik qurilma yoki simulator’da alohida sinalishi kerak.

Critical screen testlar `tests/home.test.tsx` da, web Vitest konfiguratsiyasi orqali native primitiv mocklari bilan ishlaydi. Ular haqiqiy iOS/Android runtime testi o‘rnini bosmaydi.

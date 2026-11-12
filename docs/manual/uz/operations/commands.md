# Boshqaruv buyruqlari maʼlumotnomasi

- Kim uchun: IT operatorlari
- Qamrov: ushbu repozitoriydagi Ninefruits ilovalari roʻyxatdan oʻtkazgan barcha buyruqlar (`ninefruits/*/management/commands/`) va ekspluatatsiyada ishlatiladigan Djangoning oʻrnatilgan buyruqlari. Yangi buyruq qoʻshilganda bu hujjatga ham (barcha 16 tilda) `### \`command\`` yozuvi qoʻshilishi shart, aks holda CI muvaffaqiyatsiz tugaydi (`tests/tooling/test_command_documentation.py`).

## Umumiy qoidalar

Har bir buyruq `uv run manage.py {command}` sifatida ishga tushiriladi. Docker ishlab chiqish muhitida `docker compose exec app uv run manage.py {command}`.

| Band | Qoida |
|---|---|
| Nomi | Asl tizimdagi `{context}:{action}` `{context}_{action}` ga aylanadi (Django buyruq nomlarida `:` boʻlishi mumkin emas). Misol: `term:close` → `term_close` |
| Audit yozuvi | Maʼlumotlarni oʻzgartiradigan buyruqlar (quyida "Audit: qayd etiladi") har bir ishga tushirishda buyruq, argumentlar, parametrlar, OT foydalanuvchisi, chiqish kodi va natijani faoliyat jurnaliga (log `command`) yozadi. Ularni boshqaruv panelida **Audit > Faoliyat jurnali** boʻlimida tekshiring |
| Ishga tushirish ID si | Har bir ishga tushirish soʻrov ID si oʻrniga `cmd-` bilan boshlanadigan ID oladi. Faoliyat jurnali, oʻsha ishga tushirish kiritgan maʼlumot oʻzgarishlari va u joʻnatgan Celery vazifalari bir xil ID ga ega, shuning uchun "bu oʻzgarishni qaysi buyruq kiritgan" degan savolga ID orqali javob topiladi. `--actor` operator tomonidan berilgan qiymat, shuning uchun u maʼlumot oʻzgarishlarining foydalanuvchi ustuniga yozilmaydi (haqiqiy ijrochi — OT foydalanuvchisi) |
| `--actor=<email>` | Barcha audit qilinadigan buyruqlar uchun umumiy. Masʼul administrator hisobini qayd etadi. Notanish e-pochta ishga tushirishni toʻxtatadi |
| `--dry-run` | Hech narsani oʻzgartirmasdan natijani chiqaradi. Bekor qilish qiyin boʻlgan amallarda mavjud |
| `--force` | Tasdiqlash soʻrovlarisiz ishga tushiradi (rejalar va joriy etish skriptlari uchun) |
| `--reason=` | Sabab talab qiladigan buyruqlarda mavjud |
| Chiqish kodlari | 0 muvaffaqiyat, 1 muvaffaqiyatsizlik yoki bekor qilindi, 2 tekshiruv buyrugʻi muammo topdi |
| MB konteksti | Buyruq ishlayotganda MB sessiyasi ijrochisi `system:command:{command}` ga oʻrnatiladi va maʼlumot oʻzgarishlarida (trigger) koʻrinadi |

## Djangoning oʻrnatilgan buyruqlari

### `migrate`

- Vazifasi: maʼlumotlar bazasi migratsiyalarini qoʻllaydi. Django buyrugʻi atrofidagi Ninefruits oʻrami: `--database` berilmasa, sxema egasi ulanishidan (`migrator`, rol `app_migrator`) foydalanadi. Ilova ulanishida (`app_runtime`) DDL huquqlari yoʻq. `showmigrations` va `sqlmigrate` ham standart holatda `migrator` ulanishidan foydalanadi.
- Qachon: birinchi oʻrnatishda va har bir joriy etishda (`setup_install` ham uni bajaradi).
- Parametrlar: Django `migrate` dagi bilan bir xil (`app_label`, `migration_name`, `--plan`, `--check`, `--database`).
- Audit: qayd etilmaydi (sxema oʻzgarishlari `django_migrations` migratsiyalar tarixida saqlanadi)
- Misollar

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- Muvaffaqiyatsiz boʻlsa: ruxsat xatolarida [oʻrnatish qoʻllanmasi](installation.md) dagi maʼlumotlar bazasi rollarini tayyorlashni (`db/sql/roles/`) tekshiring.

### `collectstatic`

- Vazifasi: Vite yigʻish natijasini (`static/dist/`) hamda Django va unfold statik fayllarini `STATIC_ROOT` (`staticfiles/`) ga yigʻadi. Bu katalogni veb-server (Nginx) uzatadi.
- Qachon: har bir joriy etishda, `npm ci && npm run build` dan keyin.
- Parametrlar: `--noinput` (soʻrovlarsiz), `--clear` (yigʻishdan oldin mavjud fayllarni oʻchirish).
- Audit: qayd etilmaydi
- Misollar

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- Vazifasi: tarjima fayllarini (`.po`) ishlash vaqtidagi `.mo` fayllarga kompilyatsiya qiladi. `.mo` fayllar repozitoriyda saqlanmaydi, shuning uchun buni har bir oʻrnatish va joriy etishda bajaring. Tizimda `gettext` oʻrnatilgan boʻlishi kerak.
- Qachon: har bir joriy etishda va tarjima fayllarini tahrirlagandan keyin.
- Parametrlar: `--locale=` (masalan, `ko`, `zh_Hans`, `lo`), `--ignore=.venv`.
- Audit: qayd etilmaydi
- Misollar

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- Vazifasi: **ishlatilmaydi.** Django superfoydalanuvchisi rollar va ruxsatlar katalogini hamda audit izini chetlab oʻtadi, shuning uchun bu buyruq xato bilan (chiqish kodi 1) tugaydi va `security_create_administrator` ga yoʻnaltiradi.
- Oʻrniga: birinchi administratorni `security_create_administrator` bilan yarating (tizim administratori rolini tayinlash va audit yozuvini oʻz ichiga oladi).
- Audit: tegishli emas

## Oʻrnatish va demo (1-bosqich)

### `setup_install`

- Vazifasi: yangi oʻrnatish va yangilash. Quyidagilarni ketma-ket bajaradi: migratsiyalar, zaruriy maʼlumotlar (rol shablonlari va ruxsatlarni sinxronlash, mamlakatlar, tillar, kodlar roʻyxati turlari, tashkiliy birlik turlari), muassasa sozlamalari, baholash shkalasi, oʻrnatish profillari va birinchi administrator. Qayta ishga tushirish xavfsiz (mavjud maʼlumotlar va administratorlar oʻzgartirgan qiymatlar saqlanadi).
- Qachon: birinchi oʻrnatishda va har bir joriy etishda.
- Parametrlar: `--institution-name=`, `--locale=` (standart til), `--timezone=` (masalan, `Asia/Seoul`), `--profile=` (oʻrnatish profili kaliti, takrorlanishi mumkin: `korean-university`, `yust-legacy`), `--grade-scale=` (baholash shkalasi `4.5` yoki `4.3`; bir marta oʻrnatilgach oʻzgarmaydi; boʻsh boʻlsa, birinchi profilning shkalasi), `--admin-email=`, `--admin-name=`, `--force` (savollarsiz; administrator paroli standart kirishdan oʻqiladi).
- Audit: qayd etiladi (qoʻllangan profillar, administrator yaratilganmi)
- Misollar

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="Demo University" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="Administrator"
  ```

- Natijani oʻqish: har bir qadam uchun `DONE`. `Administrator exists` tizim administratori tayinlovi mavjudligini, shuning uchun yaratish oʻtkazib yuborilganini bildiradi.
- Muvaffaqiyatsiz boʻlsa: kalit yetishmasligi haqidagi xato `DJANGO_SECRET_KEY` va `pii_generate_key` yaratgan qiymatlar muhitda oʻrnatilishi kerakligini bildiradi. Migratsiya muvaffaqiyatsiz boʻlsa: maʼlumotlar bazasi rollarini tekshiring ([oʻrnatish](installation.md)). `The grade scale is fixed` `--grade-scale` allaqachon belgilangan shkaladan farq qilishini bildiradi.

### `setup_demo`

- Vazifasi: xayoliy universitet yaratadi (tashkiliy birliklar, taʼlim dasturlari, binolar va auditoriyalar, bugungi kun atrofidagi oʻtgan, joriy va keyingi semestr ularning muddatlari bilan, Koreya universiteti profili). Har bir rol uchun qatʼiy belgilangan demo hisoblarni chiqaradi (`registrar@demo.test` va boshqalar, parol `demo-password`). Hajmlar ommaviy qoʻshish bilan yaratiladi.
- Qachon: ishlab chiqish, oʻqitish va namoyish muhitlari. **U production muhitida (`DJANGO_ENV=production`) hatto `--force` bilan ham ishlamaydi.**
- Parametrlar: `--size=tiny|small|medium|large` (taxminan 20/100/2 000/20 000 talaba; `tiny` testlar va tezkor tekshiruvlar uchun), `--seed=` (bir xil qiymat — bir xil maʼlumotlar), `--force` (tasdiqlashsiz).
- `--student-accounts`: har bir oʻqiyotgan talabaga hisob beradi va shaxsiy omborga `load-accounts.csv` (e-pochta, parol) ni yozadi, yuklama testlari uchun ([yuklama testi](load-testing.md)).
- Audit: qayd etiladi (hajm, seed, davomiylik)
- Misol: `uv run manage.py setup_demo --size=small --seed=42 --force`
- Muvaffaqiyatsiz boʻlsa: zaruriy maʼlumotlarsiz demo hisoblar oʻtkazib yuboriladi (ularning rollari yoʻq); avval `setup_install` ni bajaring. Xuddi shu bazada qayta ishga tushirish mavjud demo maʼlumotlarni oʻtkazib yuboradi.

## Asosiy maʼlumotlar va semestrlar (1-bosqich)

### `reference_import`

- Vazifasi: asosiy maʼlumotlarni CSV dan import qiladi; boshqaruv panelidagi **CSV import qilish** bilan bir xil qoidalar (qatorlar kod boʻyicha topilib yangilanadi, boʻsh tarjima kataklari mavjud qiymatni saqlaydi, xatoli qatorlar alohida saqlanadi).
- Argumentlar: `type` — `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`, `students` (talaba yozuvlari), `instructors`, `courses` (fan versiyalari), `registration_holds` (yozilish cheklovlari) / `file` — sarlavha qatoriga ega UTF-8 CSV.
- Parametrlar: `--actor=` (majburiy; import shu hisob nomidan qayd etiladi va natijasi shu hisobning **CSV importlar** ekranida koʻrinadi), `--chunk=100` (bitta Celery vazifasidagi qatorlar soni), `--dry-run` (faqat sarlavhani tekshirish va qatorlarni sanash).
- Audit: qayd etiladi (tur, fayl nomi, qatorlar, import raqami, xatoli qatorlar)
- Ustunlar formati: [administrator qoʻllanmasining 9-bobi](../admin/09-csv-import.md).
- Chiqish kodlari: vazifalar darhol bajarilsa (eager workerlar), natija chiqariladi va xatoli qatorlar 2 beradi. Import faqat navbatga qoʻyilsa, 0. Natija va xatoli qatorlar CSV fayli boshqaruv panelidagi **Asosiy maʼlumotlar > CSV importlar** boʻlimida.
- Misol: `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- Vazifasi: berilgan vaqtda davom etayotgan semestrlarni va ochiq jarayon muddatlarini (turi, semestr, mashgʻulotlar davri, nomi, qamrov mezonlari, tugash vaqti) koʻrsatadi. Semestr va muddat sozlamalarini tekshirish yoki "nega fanlarga yozilish ochilmagan?" kabi savollar uchun ishlatiladi.
- Parametrlar: `--at=` (standart — hozir; masalan, `"2027-02-15 09:00"`; vaqt mintaqasi koʻrsatilmasa, server vaqt mintaqasi (UTC) qoʻllanadi; `"2027-02-15 09:00 Asia/Seoul"` yoki `2027-02-15T09:00+09:00` mintaqani koʻrsatadi).
- Audit: qayd etilmaydi (faqat oʻqish)
- Natijani oʻqish: sanalar muassasa vaqt mintaqasida baholanadi. Rejalashtirilgan yoki arxivlangan semestrlarning muddatlari hech qachon ochilmaydi. Tugash vaqtlari muassasa vaqt mintaqasida koʻrsatiladi.

## Xavfsizlik (0, 2-bosqichlar)

### `security_create_administrator`

- Vazifasi: tizim administratori roliga ega hisob yaratadi. Odatda `setup_install` tomonidan chaqiriladi.
- Parametrlar: `--email=`, `--name=`, `--password-stdin` (parol standart kirishdan. Interaktiv boʻlmagan ishga tushirishlar uchun majburiy).
- Audit: qayd etiladi (yaratilgan foydalanuvchi ID si)
- Misol: `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator"`
- Misol (interaktiv boʻlmagan): `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator" --password-stdin`
- Muvaffaqiyatsiz boʻlsa: `system_administrator role is missing` avval `setup_install` bajarilishi kerakligini bildiradi. Parol kamida 12 belgidan iborat boʻlishi kerak.

### `security_sync_permissions`

- Vazifasi: MB dagi ruxsatlar roʻyxatini koddagi ruxsatlar katalogi bilan moslashtiradi. Yangi ruxsatlar yaratiladi; katalogda yoʻq ruxsatlar oʻchiriladi (va barcha rollardan olib tashlanadi). Tizim rollari har doim barcha ruxsatlarni oladi.
- Qachon: joriy etishdan keyin (`setup_install` buni zaruriy maʼlumotlar qadamining bir qismi sifatida bajaradi).
- Parametrlar: `--dry-run` (faqat yaratish/oʻchirish roʻyxatini chiqaradi), `--force` (oʻchirishni tasdiqlashni oʻtkazib yuboradi).
- Audit: qayd etiladi (yaratilgan/oʻchirilgan ruxsatlar)
- Natijani oʻqish: `create` va `delete` qatorlari. Oʻchirishlar boʻlsa, tasdiqlash soʻrovi chiqadi.
- Muvaffaqiyatsiz boʻlsa: tasdiqlashga "yoʻq" deb javob berish 1 kodi bilan chiqadi va hech narsani oʻzgartirmaydi.

### `security_reencrypt_secrets`

- Vazifasi: `DJANGO_SECRET_KEY` almashtirilgandan keyin undan hosil qilingan kalit bilan himoyalangan sirlarni (autentifikator ilovasi TOTP sirlari, tiklash kodlari urugʻlari, SSO mijoz sirlari) yangi kalit bilan qayta shifrlaydi. Ungacha ular `DJANGO_SECRET_KEY_FALLBACKS` dagi oldingi kalit bilan oʻqiladi. Oldingi kalitni olib tashlashdan oldin bajaring ([kalitlarni boshqarish](security-keys.md)).
- Argumentlar/parametrlar: `--dry-run` (faqat hali oldingi kalit bilan shifrlangan sirlarni sanaydi).
- Audit: qayd etiladi (sonlar)
- Natijani oʻqish: `Dry run: 0 authenticator(s) and 0 SSO client secret(s) use a previous key.` oldingi kalitni olib tashlash mumkinligini bildiradi. `cannot be decrypted` qiymatni sozlangan birorta kalit bilan oʻqib boʻlmasligini bildiradi: oldingi kalitni `DJANGO_SECRET_KEY_FALLBACKS` ga qoʻying va qayta ishga tushiring.
- Misol: `uv run manage.py security_reencrypt_secrets --dry-run`

### `security_reset_mfa`

- Vazifasi: foydalanuvchining ikki bosqichli autentifikatsiyasini (autentifikator ilovasi, e-pochta kodlari, tiklash kodlari, eslab qolingan qurilmalar) tiklaydi. Foydalanuvchi keyingi kirishda uni qaytadan ulaydi. Hech bir administrator boshqaruv paneliga kira olmaganda foydalaning (masalan, yagona administrator telefonini yoʻqotganda). Boshqa hollarda boshqaruv panelidagi **Foydalanuvchilar > Ikki bosqichli autentifikatsiyani tiklash** dan foydalaning.
- Argumentlar/parametrlar: `{user}` foydalanuvchi e-pochtasi, `--reason=` (majburiy), `--actor=` (majburiy. Tiklash haqida qaror qabul qilgan administrator).
- Audit: qayd etiladi (sabab bilan birga faoliyat jurnalida ham, xavfsizlik jurnalida ham)
- Misol: `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="Phone lost, identity verified by phone call" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- Vazifasi: koʻp marta notoʻgʻri parol kiritilgani sababli bloklangan hisobni blok muddati tugashidan oldin blokdan chiqaradi. Boshqaruv panelidagi **Foydalanuvchilar > Kirishni blokdan chiqarish** bilan bir xil.
- Argumentlar/parametrlar: `{user}` foydalanuvchi e-pochtasi, `--reason=` (majburiy).
- Audit: qayd etiladi (xavfsizlik jurnalida ham)
- Natijani oʻqish: `The account is not locked.` hech narsa oʻzgartirilmaganini bildiradi.
- Eslatma: blok chegaralari (muvaffaqiyatsiz urinishlar, blok davomiyligi) boshqaruv panelidagi **Sozlamalar > Kirish usullari** boʻlimida belgilanadi.

## Shaxslar va talaba yozuvlari (2-bosqich)

### `people_find_duplicates`

- Vazifasi: bir shaxs boʻlib koʻrinadigan shaxslarni roʻyxat qilib chiqaradi. Mezonlar: bir xil JShShIR (qidiruv xeshi) yoki bir xil lotinlashtirilgan ism va tugʻilgan sana. Birlashtirilgan shaxslar hisobga olinmaydi.
- Parametrlar: `--limit=100` (chiqariladigan guruhlar soni).
- Audit: qayd etilmaydi (faqat oʻqish)
- Chiqish kodlari: takror nomzodlar mavjud boʻlsa 2.
- Keyingi qadam: har bir guruhni boshqaruv panelidagi **Shaxslar** boʻlimida koʻrib chiqing va agar ular bir shaxs boʻlsa, saqlab qolinadigan shaxs sahifasidan **Takrorni birlashtirish** ni bajaring. Birlashtirishni bekor qilib boʻlmaydi ([administrator qoʻllanmasining 14-bobi](../admin/14-merge-and-invitations.md)).
- Misol: `uv run manage.py people_find_duplicates --limit=50`

## Qabul (3-bosqich)

### `admission_matriculate`

- Vazifasi: qabul mavsumining oʻqishga kirishi tasdiqlangan abituriyentlari uchun talaba yozuvlarini (yangi talaba raqamlari) yaratadi. Boshqaruv panelidagi **Qabul > Arizalar** boʻlimidagi ommaviy **Talaba yozuvini yaratish** bilan bir xil (`MatriculateApplicant`). Har bir abituriyent alohida qayta ishlanadi, shuning uchun bitta muvaffaqiyatsizlik boshqalarni toʻxtatmaydi.
- Argumentlar/parametrlar: `cycle` qabul mavsumi kodi, `--term=` (majburiy; qabul semestri kodi, masalan, `2027-SP`; qabul sanasi semestrning birinchi kuni), `--actor=` (majburiy; `Qabul qilingan abituriyentlar uchun talaba yozuvlarini yaratish` ruxsatiga ega hisob; faqat shu hisob qamrovidagi abituriyentlar qayta ishlanadi), `--dry-run` (faqat roʻyxat).
- Audit: qayd etiladi (mavsum, semestr, nomzodlar, yaratilganlar, muvaffaqiyatsiz ariza raqamlari). Har bir abituriyent uchun faoliyat yozuvi (`application.matriculated`) ham yoziladi.
- Chiqish kodlari: mavsum yoki semestr kodi notanish boʻlsa yoki `--actor` yoʻq boʻlsa 1, biror abituriyent muvaffaqiyatsiz boʻlsa 2.
- Misol: `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- Muvaffaqiyatsiz boʻlsa: `Only accepted offers without a student record ...` abituriyentning yozuvi allaqachon borligini yoki tasdiqlamaganini bildiradi; `The program is not in effect on the admission date.` taʼlim dasturi qabul sanasida amalda emasligini bildiradi (Asosiy maʼlumotlar > Taʼlim dasturlari boʻlimida dasturning amal qilish davrini tekshiring); `not in your scope` ariza `--actor` hisobining qamrovidan tashqarida ekanini bildiradi.

### `admission_expire_drafts`

- Vazifasi: yopilgan mavsumlarning qoralama arizalarini va belgilangan muddat davomida oʻzgartirilmagan qoralamalarni (**Sozlamalar > Qabul > Tegilmagan qoralamalar muddati (kun)**, standart 90) **Muddati oʻtgan** deb belgilaydi. Muddati oʻtgan arizalar oʻsha mavsumga yangi ariza berishga endi toʻsqinlik qilmaydi.
- Qachon: rejalashtirilgan, har kuni 03:10 da (Celery beat vazifasi `admission.expire_drafts` shu buyruqni bajaradi).
- Parametrlar: `--dry-run` (faqat sanash).
- Audit: qayd etiladi (muddati oʻtganlar soni)
- Misol: `uv run manage.py admission_expire_drafts --dry-run`

## Fan guruhlari (4-bosqich)

### `section_copy`

- Vazifasi: yangi semestr rejalashtirishini oldingi semestrning fan guruhlaridan boshlaydi. Boshqaruv panelidagi **Fan guruhlari > Boshqa semestrdan nusxalash** bilan bir xil (`CopySections`). Bekor qilinmagan fan guruhlarini qoralama sifatida oʻqituvchilar (hali ishlayotgan boʻlsa), dars vaqtlari va auditoriyalar, oʻrin taqsimotlari (boʻshatish vaqtlari semestrlar boshlanish sanalari orasidagi farqqa siljitiladi) va sillabus (yopiq qoralama sifatida) bilan birga nusxalaydi. Fan versiyasi yangi mashgʻulotlar davri boshida amalda boʻlgan versiya bilan almashtiriladi.
- Argumentlar/parametrlar: `from-term`, `to-term` semestr kodlari (masalan, `2026-FA`), `--org-unit=` (faqat shu tashkiliy birlik kodidagi fan guruhlari; takrorlanishi mumkin), `--dry-run` (nusxalashni tranzaksiyada bajarib, orqaga qaytaradi, shuning uchun hisobot aniq), `--actor=` (majburiy. Faqat shu hisobning `Fan guruhlarini rejalashtirish` ruxsati qamrovidagi fan guruhlari nusxalanadi).
- Audit: qayd etiladi (manba va maqsad semestr, nusxalangan, oʻtkazib yuborilgan va koʻrib chiqishni talab qiladiganlar soni; haqiqiy nusxalash `sections.copied` faoliyat hodisasini ham qayd etadi)
- Natijani oʻqish: `skipped` maqsadli semestrda allaqachon xuddi shu fan guruhi kodi borligini yoki amaldagi fan versiyasi yoʻqligini bildiradi; `note` fan guruhi nusxalangani, lekin biror narsa tushib qolganini bildiradi (auditoriya allaqachon band boʻlgani uchun auditoriyasiz nusxalangan, ishdan ketgan oʻqituvchi va h.k.). Mashgʻulotlar davrlari kod boʻyicha moslashtiriladi; mos kelmasa, fan guruhi butun semestrlik mashgʻulotlar davriga joylanadi.
- Chiqish kodlari: notanish semestr kodi yoki `--actor` yoʻq boʻlsa 1.
- Misol: `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- Vazifasi: dars jadvalini eʼlon qilishdan oldin semestrning fan guruhlarini tekshiradi. Auditoriyalar va oʻqituvchilarning ikki marta band qilinishining oldi MB tomonidan allaqachon olinadi; bu buyruq MB ruxsat beradigan muammolarni topadi: auditoriya sigʻimidan ortiq sigʻim, mashgʻulotlar davri boshlanish sanasida amalda boʻlmagan fan versiyasi, ishdan ketgan oʻqituvchi, sigʻimdan ortiq oʻrin taqsimotlari, mashgʻulotlar davridan tashqaridagi dars sanalari. Shuningdek, zaxiradan tiklash kabi cheklovlarsiz kirib kelgan maʼlumotlardagi auditoriya toʻqnashuvlarini ham tekshiradi.
- Argumentlar: `term` semestr kodi.
- Audit: qayd etilmaydi (faqat oʻqish)
- Chiqish kodlari: muammolar mavjud boʻlsa 2, notanish semestr kodi uchun 1. Hali oʻqituvchi, auditoriya yoki dars vaqti yoʻq fan guruhlari faqat maʼlumot uchun koʻrsatiladi (`Note`).
- Misol: `uv run manage.py schedule_check_conflicts 2027-SP`

## Fanlarga yozilish (5-bosqich)

### `registration_preflight`

- Vazifasi: fanlarga yozilishni ochishdan oldin semestrni tekshiradi. Fanlarga yozilish va qoʻshish/chiqish muddatlarini, qoidalar toʻplamini, eʼlon qilingan fan guruhlari sonini, sigʻimi 0 boʻlgan fan guruhlarini, sigʻimdan ortiq oʻrin taqsimotlarini, mashgʻulotlar davri boshlanish sanasida amalda boʻlmagan fan versiyalarini, kredit chegarasi bilan qamrab olinmagan faol talabalar sonini va fanlarga yozilish cheklovi qoʻyilgan talabalar sonini koʻrsatadi.
- Argumentlar: `term` semestr kodi (masalan, `2027-SP`).
- Audit: qayd etilmaydi (faqat oʻqish)
- Chiqish kodlari: muammolar mavjud boʻlsa 2. Qoidalar toʻplamining yoʻqligi muammo sifatida emas, maʼlumot sifatida koʻrsatiladi (qoidalarning standart qiymatlari qoʻllanadi).
- Misol: `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- Vazifasi: talaba hozir (yoki berilgan vaqtda) fan guruhiga yozilsa nima boʻlishini qoidama-qoida koʻrsatadi. Hech narsa saqlanmaydi va urinish qayd etilmaydi. "Nega yozila olmayapman?" kabi savollar uchun foydalaning.
- Argumentlar: `student-number` talaba raqami, `section` `fan kodi-guruh kodi` (masalan, `CSE2010-01`).
- Parametrlar: `--term=` (semestr kodi. Standart — shu fan guruhi mavjud boʻlgan eng soʻnggi semestr), `--at=` (baholash vaqti. Masalan, `"2027-02-10 10:00 Asia/Seoul"`).
- Audit: qayd etilmaydi (faqat oʻqish)
- Natijani oʻqish: har bir qoida uchun oʻtdi/oʻtmadi, bloklash/ogohlantirish va xabar. Qoidadan istisno bilan qamrab olingan qoida oʻtmagan deb koʻrsatiladi, lekin bloklamaydi. Sigʻim qoidalar jadvali ostida alohida koʻrsatiladi.
- Chiqish kodlari: fanga yozilish rad etiladigan boʻlsa 2.
- Misol: `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- Vazifasi: boʻsh oʻrinlari bor fan guruhlariga kutish roʻyxatidagi talabalarni navbat tartibida yozadi. Oʻtkazishda barcha qoidalar qayta tekshiriladi; biror qoidadan oʻtmagan kutish roʻyxati yozuvlari kutish roʻyxatidan olib tashlanadi (sababi qayd etiladi). Fanlarga yozilish va qoʻshish/chiqish muddatlari ikkalasi ham yopilgan fan guruhlarining kutish roʻyxatlari muddati tugaydi. Talabalar natijani e-pochta orqali oladi.
- Argumentlar/parametrlar: `term?` semestr kodi (standart: kutish roʻyxati yozuvlari bor barcha semestrlar), `--actor=`.
- Audit: qayd etiladi (fan guruhlari, oʻtkazilganlar, olib tashlanganlar, muddati tugaganlar soni)
- Qachon: fandan chiqish, voz kechish yoki oʻrin taqsimotini boʻshatishda tegishli fan guruhi navbat vazifasi orqali darhol qayta ishlanadi. Bu buyruq esa tushib qolgan narsalarni qayta ishlaydigan, har soatda rejalashtirilgan sugʻurta vositasidir.
- Misol: `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- Vazifasi: boʻshatish vaqti oʻtgan oʻrin taqsimotlarini (masalan, mutaxassislik talabalari uchun band qilingan oʻrinlar) qayta ishlangan deb belgilaydi va oʻsha fan guruhlari uchun kutish roʻyxatidan oʻtkazish vazifasini navbatga qoʻyadi. Band qilingan oʻrinlar boʻshatish vaqti oʻtishi bilanoq hisob-kitobda umumiy oʻrinlarga aylanadi, shuning uchun bu buyruq oʻrinlarni faqat kutish roʻyxatiga topshiradi.
- Audit: qayd etilmaydi (har 5 daqiqada ishlaydi. Oʻtkazish natijalari fanlarga yozilish yozuvlarida)
- Qachon: rejalashtirilgan (har 5 daqiqada, Celery beat vazifasi `registration.release_reserved_seats`). Oʻtkazish vazifasi har bir fan guruhi uchun `registration.promote_waitlist` (Redis qulfi orqali har bir fan guruhi uchun bir vaqtda bittadan).
- Misol: `uv run manage.py registration_release_reserved_seats`

## Baholar (6-bosqich)

### `term_close`

- Vazifasi: semestrni yopadi. Semestrdagi barcha baholar yakunlangan boʻlishi kerak. Har bir talabalar boʻlagi (100) uchun semestr natijasini (kreditlar, semestr va umumiy GPA) hisoblaydi, akademik holatni (yaxshi holat, akademik ogohlantirish, chetlashtirishni koʻrib chiqish) va imtiyozlarga muvofiqlikni aniqlaydi (Celery chord ining `grading.close_term_records` vazifalari); soʻngra yakunlovchi vazifa `grading.finish_term_close` imtiyozlarni har bir taʼlim dasturi boʻyicha reytinglaydi, semestr natijalarini rasmiy yozuv sifatida yopadi va semestrni **Baholar yopilgan** holatiga oʻtkazadi. Jarayon `job_batches` da saqlanadi va **Baholar > Semestr natijalari** roʻyxati ustida koʻrsatiladi. Tugagach, uni boshlagan xodim e-pochta xatini oladi. Boshqaruv panelidagi **Baholar > Semestr natijalari > Semestrni yopish** bilan bir xil.
- Argumentlar/parametrlar: `term` semestr kodi, `--dry-run` (faqat semestrni yopish mumkinligini tekshiradi), `--reason=` (yozuvda saqlanadigan sabab), `--actor=`.
- Audit: qayd etiladi (talabalar soni, baholari yakunlanmagan fan guruhlari soni, paket ID si). Yopish tugagach, `term.closed` audit yozuvida akademik ogohlantirishlar, chetlashtirishni koʻrib chiqishlar va imtiyozlar soni saqlanadi.
- Chiqish kodlari: baʼzi fan guruhlarida yakunlanmagan baholar boʻlsa 2 (har bir fan guruhi boʻyicha yakunlanmaganlar soni chiqariladi). Semestr eʼlon qilingan holatda boʻlmasa 1.
- Qachon: baho kiritish va yakunlash tugallangandan keyin. Paketni Flower va semestr natijalari ekranida kuzating. Celery workersiz semestr holati oʻzgarmaydi. Maʼlumotlar bazasi xatosi bilan muvaffaqiyatsiz boʻlgan boʻlak 3 martagacha qayta uriniladi; baribir muvaffaqiyatsiz boʻlsa, paket muvaffaqiyatsiz holatda qoladi va semestr oʻzgarmaydi (sababini bartaraf eting va qayta ishga tushiring; qayta ishga tushirish bir xil natija beradi).
- Misollar: `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py term_close 2026-FA --reason="Fall 2026 grades closed" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- Vazifasi: yakunlangan baholardan semestr natijalarini (kreditlar, semestr va umumiy GPA) qayta hisoblaydi. Oʻzgartirilgan baholash siyosatini (GPA kasr xonalari, qayta oʻqishni hisobga olish) oʻtgan semestrlarga qoʻllash uchun foydalaning. Akademik holat va imtiyozlar semestr yopilganda belgilangan qiymatlarni saqlaydi. Tasdiqlangan bahoni oʻzgartirish oʻsha talabani avtomatik ravishda qayta hisoblaydi, shuning uchun buning uchun bu buyruq kerak emas.
- Parametrlar: `--term=` (oʻsha semestrda baholari bor talabalar, oʻsha semestrdan boshlab), `--student-number=` (bitta talaba), `--reason=` (majburiy), `--actor=`.
- Audit: qayd etiladi (talabalar soni, sabab)
- Chiqish kodlari: sababsiz yoki notanish semestr kodi yoki talaba raqami uchun 1.
- Misol: `uv run manage.py grades_recalculate --term=2026-SP --reason="GPA changed to three decimal places"`

### `grades_remind_missing`

- Vazifasi: baholari hali topshirilmagan (kiritilmagan yoki qoralama sifatida saqlangan) fan guruhlarining oʻqituvchilariga e-pochta yuboradi. Fan guruhlari har bir oʻqituvchi boʻyicha bitta xatga guruhlanadi.
- Argumentlar/parametrlar: `term` semestr kodi, `--dry-run` (yubormasdan maqsadlarni chiqaradi), `--actor=`.
- Audit: qayd etiladi (fan guruhlari, oʻqituvchilar, yuborilgan xatlar)
- Qachon: baho kiritish muddati yopilishidan bir necha kun oldin. Kerak boʻlsa, uni rejaga qoʻshing.
- Misol: `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## Fan soʻrovnomasi (7-bosqich)

### `evaluation_remind`

- Vazifasi: fan soʻrovnomasi muddati ochiq paytda hali baholanmagan fanlari bor talabalarga e-pochta yuboradi. Qolgan fanlar har bir talaba boʻyicha bitta xatga guruhlanadi (oluvchining tilida).
- Argumentlar/parametrlar: `term` semestr kodi, `--dry-run` (faqat maqsadli talabalar soni, hech narsa yuborilmaydi), `--actor=`.
- Audit: qayd etiladi (maqsadli talabalar, yuborilgan xatlar)
- Chiqish kodlari: notanish semestr kodi uchun 1.
- Qachon: soʻrovnoma muddati davomida bir yoki ikki marta. Kerak boʻlsa, uni rejaga qoʻshing.
- Misol: `uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- Vazifasi: semestrning fan soʻrovnomasi natijalarini oʻqituvchilarga eʼlon qiladi. Boshqaruv panelidagi **Fan soʻrovnomasi > Semestr soʻrovnomalari > Natijalarni eʼlon qilish** bilan bir xil. Eʼlon qilingandan keyin ham natijalar faqat javoblarning minimal soni va javob berish ulushiga yetgan fan guruhlari uchun koʻrinadi.
- Argumentlar/parametrlar: `term` semestr kodi, `--actor=` (`Soʻrovnoma shakllari, semestr soʻrovnomalari va eʼlon qilishni boshqarish` ruxsatiga ega hisob; eʼlon qiluvchi sifatida qayd etiladi).
- Audit: qayd etiladi (javoblar soni, allaqachon eʼlon qilinganmi). Faoliyat hodisasi `evaluation.published`.
- Chiqish kodlari: notanish semestr kodi yoki fan soʻrovnomasi boʻlmagan semestr uchun 1.
- Qachon: soʻrovnoma muddati va baholarni qayta ishlash tugallangandan keyin. Allaqachon eʼlon qilingan semestr oʻzgartirilmaydi.
- Misol: `uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## Maʼlumotnomalar (8-bosqich)

### `certificate_verify`

- Vazifasi: maʼlumotnoma tekshirish kodini ochiq tekshirish sahifasidagi mezonlar bilan tekshiradi. Turi, seriya raqami, berilgan sanasi va niqoblangan egasini chiqaradi.
- Argumentlar/parametrlar: `code` tekshirish kodi (harflar katta-kichikligi ahamiyatsiz).
- Audit: yoʻq (faqat oʻqish)
- Chiqish kodlari: haqiqiy boʻlsa 0, notanish kod, bekor qilingan maʼlumotnoma yoki amal qilish muddati tugagan boʻlsa 2.
- Misol: `uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- Vazifasi: berilgan maʼlumotnomaning PDF faylini joriy maʼlumotlar va shablon bilan qayta yaratib, saqlangan faylni almashtiradi. Boshqaruv panelidagi **Maʼlumotnomalar > Berilgan maʼlumotnomalar > Qayta yaratish** bilan bir xil. Seriya raqami va tekshirish kodi oʻzgarmaydi; nazorat summasi oʻzgaradi. PDF Gotenberg yordamida yaratiladi.
- Argumentlar/parametrlar: `issue` seriya raqami, `--reason=` (majburiy), `--actor=` (`Maʼlumotnomalarni berish, qayta yaratish va bekor qilish` ruxsatiga ega hisob).
- Audit: qayd etiladi (seriya raqami, yangi nazorat summasi); faoliyat hodisasi `certificate.rerendered`.
- Chiqish kodlari: sababsiz, notanish seriya raqami uchun yoki PDF yaratib boʻlmasa 1.
- Qachon: shablon, ism yozilishi yoki `APP_URL` tuzatilgandan keyin muayyan maʼlumotnomani qayta yaratish uchun.
- Misol: `uv run manage.py certificate_render ENR-2026-000001 --reason="Name spelling corrected"`

## Imtihonlar (9-bosqich)

### `assessment_import_results`

- Vazifasi: imtihon sessiyasi natijalarini CSV dan kiritadi. Boshqaruv panelidagi **Imtihon sessiyalari > Natijalarni import qilish (CSV)** bilan bir xil qoidalar (faqat roʻyxatdan oʻtgan talabalar, oʻtish ballar asosida aniqlanadi, eʼlon qilinishidan oldin qayta kiritish natijani almashtiradi, eʼlon qilingandan keyin qatorlar xato sifatida koʻrsatiladi).
- Argumentlar/parametrlar: `type` imtihon turi kodi / `held_date` imtihon sanasi `YYYY-MM-DD` / `file` sarlavha qatoriga ega UTF-8 CSV, `--actor=` (majburiy, natijalarni kiritgan shaxs sifatida qayd etiladi), `--dry-run` (faqat qatorlarni tekshirish, hech narsa qayd etilmaydi).
- Ustunlar formati: [administrator qoʻllanmasining 24-bobi](../admin/24-assessments.md).
- Audit: qayd etiladi (sessiya, fayl nomi, qatorlar soni, kiritilgan/kelmagan/xato soni). Har bir natija uchun `assessment.result_recorded` faoliyat yozuvi ham yoziladi.
- Chiqish kodlari: sessiya topilmasa, faylni oʻqib boʻlmasa yoki `--actor` yoʻq boʻlsa 1; xatoli qatorlar boʻlsa 2 (qolgan qatorlar qayd etiladi).
- Misol: `uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- Vazifasi: sessiya natijalarini talabalarga eʼlon qiladi. Boshqaruv panelidagi **Imtihon sessiyalari > Natijalarni eʼlon qilish** bilan bir xil. Eʼlon qilingandan keyin natijalar faqat tuzatish soʻrovlari orqali oʻzgaradi.
- Argumentlar/parametrlar: `type` imtihon turi kodi / `held_date` imtihon sanasi, `--actor=` (majburiy, talabalarni roʻyxatga olish, natijalarni kiritish va eʼlon qilish ruxsati bilan).
- Audit: qayd etiladi (sessiya, natijalar soni) va `assessment.results_published` faoliyat yozuvi
- Chiqish kodlari: sessiya topilmasa, allaqachon eʼlon qilingan boʻlsa, `--actor` yoʻq boʻlsa yoki unda ruxsat boʻlmasa 1.
- Qachon: natijalarni kiritish tugallangandan keyin.
- Misol: `uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## Davomat (10-bosqich)

### `attendance_generate_sessions`

- Vazifasi: semestrning har bir fan guruhi uchun dars vaqtlaridan (hafta kuni, vaqt, para) darslarni yaratadi. Oʻqituvchi portalidagi **Dars vaqtlaridan yaratish** va boshqaruv panelidagi **Darslar** yorligʻidagi **Darslarni yaratish** bilan bir xil. Mavjud darslar va ularning davomati saqlanadi (qayta ishga tushirish xavfsiz). Bekor qilingan fan guruhlari oʻtkazib yuboriladi.
- Argumentlar/parametrlar: `term` semestr kodi, `--section=` (fan kodi-guruh kodi, masalan, `CSE2010-01`, faqat bittasi), `--dry-run` (faqat maqsadli fan guruhlari soni), `--actor=`.
- Audit: qayd etiladi (semestr, fan guruhlari, yaratilgan darslar)
- Qachon: semestr boshlanishidan oldin, dars vaqtlari tasdiqlangandan keyin. Dars vaqtlari oʻzgarganda qayta ishga tushiring.
- Misol: `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## Bitiruv (11-bosqich)

### `degree_audit_run`

- Vazifasi: har bir oʻqiyotgan talaba uchun bitiruv talablarini tekshirish natijasini saqlaydi. Boshqaruv panelidagi **Bitiruv talablari tekshiruvlari > Tekshiruvlarni bajarish** bilan bir xil. Eng soʻnggi saqlangan tekshiruv bitiruvni rasmiylashtirish uchun asos boʻladi. Har bir ishga tushirish yangi snapshotlar qoʻshadi.
- Parametrlar: `--term=` (tekshiruv tegishli boʻlgan semestr kodi), `--student-number=` (bitta talaba), `--min-year-level=` (faqat shu kurs va undan yuqori), `--actor=`.
- Audit: qayd etiladi (talabalar soni, talablarni bajarganlar soni). `--actor` bilan `graduation.audits_run` faoliyat hodisasi ham qayd etiladi.
- Chiqish kodlari: notanish semestr kodi uchun 1.
- Qachon: bitiruvni koʻrib chiqishdan oldin (semestr oxiri) hamda talablar toʻplamlari yoki muqobil fanlar oʻzgartirilgandan keyin.
- Misol: `uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## LMS integratsiyasi (12-bosqich)

### `lms_sync`

- Vazifasi: eʼlon qilingan fan guruhlarini platformaga uzatadi (kurs yaratish va bogʻlash, oʻqituvchilar, yozilgan talabalar). Boshqaruv panelidagi **Kurs bogʻlanishlari > Qayta sinxronlash** bajaradigan ishni butun semestr uchun bajaradi. Allaqachon bogʻlangan fan guruhlari faqat qayta taʼminlanadi (idempotent). Har bir qadam **Sinxronlash jurnallari** da saqlanadi.
- Argumentlar/parametrlar: `{platform}` platforma kodi, `--term=` (semestr kodi, standart — tugamagan barcha semestrlar), `--section=` (bitta fan kodi-guruh kodi, masalan, `CSE2010-01`), `--dry-run` (nima yuborilishini faqat "skipped" sifatida qayd etadi), `--actor=`.
- Audit: qayd etiladi (platforma, fan guruhlari, aʼzolar, muvaffaqiyatsizliklar)
- Chiqish kodlari: notanish platforma yoki semestr kodi uchun 1, biror fan guruhi muvaffaqiyatsiz boʻlsa 2 (har bir fan guruhi boʻyicha xato chiqariladi).
- Qachon: semestr boshlanishidan oldin, yangi platforma faollashtirilgandan keyin.
- Misol: `uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- Vazifasi: platformadagi kurs roʻyxatlarini talabalar axborot tizimidagi fanga yozilganlar roʻyxatlari bilan solishtiradi, yetishmayotgan aʼzolarni qoʻshadi va ortiqchalarini olib tashlaydi. Hali bogʻlanmagan fan guruhlari toʻliq sinxronlanadi. Farqlar sinxronlash jurnalida saqlanadi (`reconcile`, `payload` dagi `missing` va `extra`).
- Argumentlar/parametrlar: `{platform?}` (koʻrsatilmasa, barcha faol platformalar), `--term=` (standart — tugamagan semestrlar), `--dry-run` (faqat farqlarni qayd etadi), `--actor=`.
- Audit: qayd etiladi (har bir platforma boʻyicha fan guruhlari, qoʻshilgan/olib tashlangan/muvaffaqiyatsiz soni)
- Chiqish kodlari: notanish platforma yoki semestr kodi uchun yoki birorta platforma faol boʻlmasa 1, biror fan guruhi muvaffaqiyatsiz boʻlsa 2.
- Qachon: rejalashtirilgan, har kuni 02:30 da `lms.reconcile` vazifasi sifatida (Celery beat). Platformadagi uzilishdan keyin qoʻlda ishga tushiring.

### `api_issue_token`

- Vazifasi: hisob uchun API integratsiya tokenini beradi ([ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md)), odatda faqat kerakli ruxsatlarga ega xizmat hisobi uchun (LMS: `lms.manage`, BI: `reports.view`). Token standart chiqishning birinchi qatorida **bir marta** chiqariladi; maʼlumotlar bazasi faqat uning dayjestini saqlaydi. Soʻrovlar uni `Authorization: Token <token>` sarlavhasida yuboradi.
- Argumentlar/parametrlar: `{email}` hisob e-pochtasi, `--days=` (amal qilish muddati 1 dan 365 kungacha, standart `API_TOKEN_TTL_DAYS` = 90), `--reason=` (nima uchunligi, auditda qayd etiladi), `--actor=`.
- Audit: qayd etiladi (`api.token_issued`: kalit prefiksi va muddati; hech qachon tokenning oʻzi emas)
- Chiqish kodlari: notanish yoki faol boʻlmagan hisob yoki ruxsat etilgan oraliqdan tashqaridagi muddat uchun 1.
- Misol: `uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle callbacks" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- Vazifasi: hisobning API tokenlarini bekor qiladi (hammasini yoki `--key=` bilan bittasini). `--list` faqat tokenlarni roʻyxat qilib chiqaradi (kalit prefiksi, berilgan va tugash vaqtlari).
- Argumentlar/parametrlar: `{email}`, `--key=` (kalit prefiksi), `--list`, `--reason=`, `--actor=`.
- Audit: qayd etiladi (`api.token_revoked`: bekor qilingan kalit prefikslari)
- Chiqish kodlari: notanish hisob yoki `--key` ga mos token boʻlmasa 1.
- Qachon: integratsiya tugaganda, token sizib chiqqan boʻlishi mumkin boʻlganda yoki masʼul shaxs oʻzgarganda.

## Ekspluatatsiya tekshiruvlari va tozalash (13-bosqich)

### `system_health_check`

- Vazifasi: sozlamalar va kalitlarni (`DJANGO_SECRET_KEY`, PII kalitlari, `DEBUG`), MB ulanishi va rollarini (runtime, migrator, reporting), shaxsiy maʼlumotlar jadvallaridagi RLS ni, bajarilmagan migratsiyalarni, ruxsatlar katalogi sinxronligini, Redis, Celery workerlari, Gotenberg, shaxsiy omborga yozish va beat heartbeat ni (`core.heartbeat`, 5 daqiqa ichida) tekshiradi.
- Parametrlar: `--json` (monitoring uchun chiqish).
- Audit: yoʻq (faqat oʻqish)
- Chiqish kodlari: biror tekshiruv muvaffaqiyatsiz boʻlsa 2.
- Qachon: joriy etishdan darhol keyin, nosozlik gumon qilinganda, monitoring orqali muntazam. Yuklama muvozanatlagichlari `/api/v1/health/` dan foydalanadi.
- Misol

  ```bash
  uv run manage.py system_health_check
  uv run manage.py system_health_check --json
  ```

### `audit_seal`

- Vazifasi: audit jadvallarining (`audit.record_changes`, `audit.activity_log`, `audit.security_events`) yangi qatorlarini xesh zanjiriga bogʻlaydi ([audit yaxlitligi](audit-and-maintenance.md)). Sxema egasi ulanishida (`migrator`) ishlaydi.
- Parametrlar: `--table=` (record_changes, activity_log, security_events dan biri; takrorlanishi mumkin), `--actor=`.
- Audit: qayd etiladi (har bir jadval boʻyicha muhrlangan qatorlar)
- Qachon: rejalashtirilgan, har kuni 03:30 da.
- Misol

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- Vazifasi: soxtalashtirish, oʻchirish va tartib oʻzgarishini aniqlash uchun audit qatorlarining mazmun xeshlari va zanjirini qayta hisoblaydi. Har bir jadval boʻyicha tekshirilgan qatorlar, muhrlangan qatorlar, nomuvofiqliklar va birinchi nomuvofiq ID ni chiqaradi.
- Parametrlar: `--table=`.
- Audit: yoʻq (faqat oʻqish)
- Chiqish kodlari: nomuvofiqlik boʻlsa 2.
- Qachon: zaxiralashdan oldin, xavfsizlik tekshiruvlari paytida, tozalashdan keyin.

### `audit_prune`

- Vazifasi: saqlash muddati oʻtgan **muhrlangan** audit qatorlarini oʻchiradi. Sxema egasi ulanishida `app.audit_maintenance = on` bilan tranzaksiyada ishlaydi. Muhrlanmagan qatorlar saqlanadi (avval `audit_seal` ni bajaring). Har bir oʻchirish `audit.pruned` xavfsizlik hodisasini qayd etadi (jadval, chegara sanasi, oʻchirilgan qatorlar, ID oraligʻi, chegara qatorining `chain_hash` i).
- Parametrlar: `--before=YYYY-MM-DD` (majburiy; oʻsha kun yarim tunidan oldingi qatorlar), `--table=`, `--dry-run` (faqat sanash), `--actor=`.
- Audit: qayd etiladi (chegara sanasi, har bir jadval boʻyicha oʻchirilgan qatorlar va ID oraligʻi)
- Qachon: saqlash siyosatiga muvofiq, zaxiralashdan keyin.
- Misol

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu
  ```

### `media_prune_orphans`

- Vazifasi: egasi endi mavjud boʻlmagan media qatorlarini va shaxsiy omborda qatori yoʻq kataloglarni (`<media id>/`) oʻchiradi (shaxslar fotosuratlari, ariza hujjatlari, maʼlumotnoma PDF fayllari, imtihon tasdiqlovchi hujjatlari).
- Parametrlar: `--dry-run` (faqat roʻyxat), `--actor=`.
- Audit: qayd etiladi (qatorlar, kataloglar)
- Qachon: har oy yoki ommaviy oʻchirishdan keyin.

## Shaxsiy maʼlumotlarni shifrlash kalitlari (0-bosqich)

### `pii_generate_key`

- Vazifasi: `PII_ENCRYPTION_KEY` va `PII_HASH_KEY` uchun yangi kalitlarni (32 bayt, `base64:...`) chiqaradi. Hech narsa saqlamaydi.
- Audit: qayd etilmaydi
- Diqqat: `PII_HASH_KEY` oʻzgartirilsa, barcha qidiruv xeshlari (`*_hash`) yaroqsiz boʻladi. Faqat shifrlash kalitini almashtiring: eski kalitni `PII_PREVIOUS_KEYS` ga oʻtkazing, soʻngra `pii_reencrypt` ni bajaring.
- Misol

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- Vazifasi: kalit almashtirilgandan keyin oldingi kalit bilan shifrlangan shaxsiy maʼlumotlarni joriy kalit bilan qayta shifrlaydi. Yozuvlar boʻlaklari boʻyicha Celery vazifalari guruhi sifatida ishlaydi. Allaqachon joriy kalitdagi yozuvlarga tegilmaydi.
- Argumentlar: shifrlangan shaxsiy maʼlumotlar maydonlariga ega model (`app_label.Model`, masalan, `person.Person`).
- Parametrlar: `--chunk=500` (bitta vazifadagi yozuvlar), `--dry-run` (faqat oldingi kalitdan foydalanayotgan yozuvlarni sanaydi), `--force` (tasdiqlashsiz), `--actor=`.
- Audit: qayd etiladi (paket ID si, vazifalar soni / oldindan koʻrish soni)
- Tekshirish: vazifalarni Flower da kuzating. Ular tugagach va `--dry-run` 0 ni koʻrsatgach, oldingi kalitni `PII_PREVIOUS_KEYS` dan olib tashlang.
- Misol

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu
  ```

## Mahalliylashtirish (0-bosqich)

### `i18n_missing`

- Vazifasi: tarjima qilinadigan satrlarni manba koddan `makemessages` kabi ajratib oladi (fayl yozmasdan), ularni barcha kataloglar (global `locale/` va har bir ilovaning `locale/` i) bilan solishtiradi va har bir til boʻyicha yetishmayotgan satrlarni (katalogda yoʻq, boʻsh `msgstr`, fuzzy, farq qiluvchi oʻrinbosarlar) va eskirgan yozuvlarni roʻyxat qilib chiqaradi.
- Argumentlar/parametrlar: `[locale]` (faqat bitta til, masalan, `ko`, `zh-hans`, `lo`), `--strict` (satrlar yetishmasa chiqish kodi 2; CI da ishlatiladi), `--no-extract` (faqat kataloglarni tekshirish, manba kodni skanerlamasdan).
- Audit: qayd etilmaydi
- Talab qiladi: GNU gettext (`xgettext`, `msguniq`).
- Misol

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- Vazifasi: tarjimonlar uchun jadval yozadi (`.xlsx` yoki `.csv`, kengaytma boʻyicha tanlanadi). Ustunlar: `catalog` (katalog joylashuvi), `context`, `source` (inglizcha msgid), `source_plural`, `translation`, `note` (asl kalit).
- Argumentlar/parametrlar: `{locale} {path}`, `--missing` (faqat tarjimasi yoʻq satrlar).
- Audit: qayd etilmaydi
- Misol: `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- Vazifasi: tarjimonlar toʻldirgan jadvalni kataloglarga (`.po`) qayta yozadi va ularni kompilyatsiya qiladi (`.mo`). Faqat kataloglarda mavjud satrlar (bir xil katalog, kontekst va inglizcha matn) import qilinadi; boʻsh tarjimalar oʻtkazib yuboriladi.
- Argumentlar/parametrlar: `{locale} {path}`, `--dry-run` (yoziladigan satrlarni roʻyxat qilib chiqarish), `--actor=`.
- Audit: qayd etiladi (til, tarjimalar soni)
- Eslatma: kataloglar repozitoriyda saqlanadi. Importdan keyin `.po` oʻzgarishlarini commit qiling.

### `i18n_makemessages`

- Vazifasi: barcha kataloglar manba kodga mos kelishi uchun repozitoriy ildizidan `makemessages` ni bajaradi (ko, zh_Hans, lo). Satrlar ilovada `locale/` boʻlsa, ilovaning `locale/` iga, aks holda global `locale/` ga tushadi. `.venv`, `tests`, `docs` va shunga oʻxshash kataloglar oʻtkazib yuboriladi.
- Parametrlar: Django `makemessages` dagidek (`-l`, `--no-obsolete`, ...).
- Audit: qayd etilmaydi
- Misol: `uv run manage.py i18n_makemessages`

## Tekshiruvlar (0-bosqich)

### `pdf_sample`

- Vazifasi: shriftlarni va PDF xizmatiga (Gotenberg) ulanishni tekshirish uchun hangul, CJK, lao, tay, devanagari, kirill va lotin yozuvlari aralash jadvalni PDF ga chiqaradi.
- Argument: `[path]` (standart `pdf-sample.pdf`, shaxsiy fayllar ombori `PRIVATE_MEDIA_ROOT` ga nisbatan).
- Audit: qayd etilmaydi
- Muvaffaqiyatsiz boʻlsa: chiqish kodi 1. Ulanish xatolarida `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` va Gotenberg konteynerini tekshiring.
- Misol: `uv run manage.py pdf_sample`

### `naming_check`

- Vazifasi: maʼlumotlar bazasi sxemasi va manba kodni [nomlash qoidalari](../../../development/naming.md) ga muvofiqligini tekshiradi. Haqiqiy maʼlumotlar bazasi katalogidagi (`public`, `audit`, `reporting` sxemalari) jadval va ustun nomlarini, Ninefruits ilovalarining migratsiya fayl nomlarini, boshqaruv buyruqlari nomlarini (`context_action`) hamda tarjima kataloglaridagi (`.po`) msgid va msgctxt larni tekshiradi.
- Qoidalar: snake_case, taqiqlangan qoʻshimchalar (`_old`, `_new`, `_backup`, `_tmp`, sanalar, raqamlar), til kodini oʻz ichiga olgan nomlar, vaqt mintaqasisiz vaqt ustunlari (`timestamp without time zone`), mantiqiy ustun nomlari (`is_`, `has_`, `can_` yoki feʼl), sana ustunlari nomlari (`_date`), semantik kalitlarga oʻxshash msgid lar (`registration.errors.x`). Django va paketlar belgilagan jadvallar (`django_*`, allauth, Celery beat, `settings`, `cache`, `jobs`, `media` va h.k.) hisobga olinmaydi.
- Parametrlar: `--database=` (tekshiriladigan maʼlumotlar bazasi ulanishi, standart `default`), `--skip-database` (faqat fayllarni tekshirish, maʼlumotlar bazasisiz).
- Audit: qayd etilmaydi
- Chiqish kodi: muammolar topilsa 2.
- Misol

  ```bash
  uv run manage.py naming_check
  ```

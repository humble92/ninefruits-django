# 11. Fan toifalari va baholash shkalalari

## Fan toifalari

Menyu: **Asosiy maʼlumotlar > Fan toifalari** (`Fan toifalarini boshqarish` ruxsati). Eski tizimdagi (YUSTIC) `SFOBJDIST` oʻrnini egallaydi.

Fanlarning tasnifi, masalan umumtaʼlim majburiy yoki mutaxassislik tanlov fani. **Yuqori** belgilash orqali toifalarni guruhlash mumkin (masalan, Umumtaʼlim → Umumtaʼlim majburiy, Umumtaʼlim tanlov). Bitiruv talablari ([17-bob](17-courses-and-curriculum.md), [26-bob](26-graduation.md)) ularga "mutaxassislik majburiy fanlaridan 30 kredit" kabi tarzda tayanadi.

## Baholash shkalalari

Menyu: **Asosiy maʼlumotlar > Baholash shkalalari** (`Baholash shkalalarini boshqarish` ruxsati). Eski tizimdagi `SSCOREDEF` oʻrnini egallaydi.

| Shkala maydoni | Tavsifi |
|---|---|
| Maksimal baho bali | Masalan, 4.5 |
| Standart | Faqat bitta shkala standart boʻlishi mumkin. Uni faqat hech bir shkala standart boʻlmaganda yoqish mumkin (quyida qarang) |

Shkalani oching va pastdagi **Baholar** boʻlimida baholarni qoʻshing.

| Baho maydoni | Tavsifi |
|---|---|
| Baho | Masalan, `A+`, `P` |
| Baho bali | GPA ga hisoblanadigan baholar uchun majburiy |
| Dan (%) / Gacha (%) | Xom ballni aylantirish oraliqlari (ixtiyoriy), masalan A+ 95–100 |
| GPA ga hisoblanadi | P/NP kabi GPA dan chiqarib tashlanadigan baholar uchun oʻchiring |
| Oʻtish bahosi | F yoki NP kabi kredit bermaydigan baholar uchun oʻchiring |
| Qoʻllanishi | Baholanadigan fanlar (harfli baholar), Oʻtdi/oʻtmadi fanlari (P, NP) yoki Ikkalasi (masalan, I — tugallanmagan). Baho kiritish ekrani faqat fanning baholash asosiga mos baholarni koʻrsatadi |

**Standart shkala oʻrnatish paytida belgilanadi va uni oʻzgartirib boʻlmaydi** (2026-10-23 dagi qaror), chunki barcha baholar va GPA shu shkalada ifodalanadi. Uni `setup_install --grade-scale=4.5|4.3` bilan belgilang; parametr berilmasa, birinchi profilning shkalasi standart boʻladi. Standart belgisini ekranda oʻzgartirib boʻlmaydi va standart shkalani oʻchirib boʻlmaydi. Har bir baho uchun ball oraliqlari va baho ballari shu ekranda tahrirlanadi ([21-bob](21-grades.md)).

Profillar yuklaydigan shkalalar

- Koreya universiteti: 4.5 shkala (`KR45`): A+ 4.5 (95–100), A0 4.0 (90–), B+ 3.5 (85–), B0 3.0 (80–), C+ 2.5 (75–), C0 2.0 (70–), D+ 1.5 (65–), D0 1.0 (60–), F 0, P, NP
- `--grade-scale=4.3` yoki eski YUST profili: 4.3 shkala (`KR43` yoki `YUST43`): A+ 4.3 (97–100), A0 4.0 (93–), A- 3.7 (90–), B+ 3.3 (87–), B0 3.0 (83–), B- 2.7 (80–), C+ 2.3 (77–), C0 2.0 (73–), C- 1.7 (70–), D+ 1.3 (67–), D0 1.0 (63–), D- 0.7 (60–), F 0, P, NP (eski profilga N va I ham kiradi). Ball oraliqlari 3 ballik qadam bilan boshlanadi, shuning uchun ularni universitet meʼyoriga moslashtiring.

Baholarda allaqachon ishlatilgan shkalani oʻchirib boʻlmaydi.

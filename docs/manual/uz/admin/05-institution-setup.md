# 5. Muassasa sozlamalari va dastlabki sozlash tartibi

## Muassasa sozlamalari

**Sozlamalar > Muassasa** boʻlimida sozlanadi (`Muassasa sozlamalarini boshqarish` ruxsati).

| Sozlama | Tavsifi |
|---|---|
| Muassasa nomi | Har bir til uchun kiritiladi. Boshqaruv panelining yuqori chap burchagida koʻrsatiladi |
| Vaqt mintaqasi | Semestr sanalari va jarayon muddatlarini aniqlash uchun asos, masalan `Asia/Seoul`. Saqlangan barcha vaqtlar shu vaqt mintaqasida koʻrsatiladi |
| Taklif qilinadigan tillar | Foydalanuvchilar tanlashi mumkin boʻlgan tillar. Roʻyxatda faqat tarjima fayllari oʻrnatilgan tillar chiqadi |
| Asosiy til | Til tanlamagan foydalanuvchilar uchun va brauzer tili nomaʼlum boʻlganda ishlatiladi |

## Yangi universitet uchun dastlabki sozlash tartibi

IT operatori `setup_install` ni yakunlagandan keyin (ekspluatatsiya qoʻllanmasi, [Oʻrnatish](../operations/installation.md)) asosiy maʼlumotlar uchun masʼul administrator maʼlumotlarni quyidagi tartibda kiritadi. Keyingi qadamlar oldingi qadamlardagi kodlarga tayanadi, shuning uchun tartibga rioya qiling.

1. **Muassasa sozlamalari**: nomi, vaqt mintaqasi, tillar (ushbu bob)
2. **Kodlar roʻyxati**: millat, qabul turi va auditoriya turi qiymatlari ([6-bob](06-code-data.md)). Agar oʻrnatish paytida Koreya universiteti profili qoʻllangan boʻlsa, auditoriya turlari allaqachon mavjud.
3. **Tashkiliy birlik turlari**ni tekshiring, soʻng **Tashkiliy birliklar**: universitet → fakultet → kafedra ([7-bob](07-org-units-and-programs.md)). Birliklar koʻp boʻlsa, CSV dan foydalaning ([9-bob](09-csv-import.md)).
4. **Taʼlim dasturlari**: har bir kafedraning taʼlim dasturlari ([7-bob](07-org-units-and-programs.md))
5. **Binolar**, **Auditoriyalar** ([8-bob](08-facilities.md), CSV bilan ham mumkin)
6. **Semestr turlari** va **Paralar**ni tekshiring ([10-bob](10-terms.md))
7. **Fan toifalari** va **Baholash shkalalari**ni tekshiring. Bitta standart shkala belgilangan boʻlishi shart ([11-bob](11-course-categories-and-grade-scales.md))
8. **Oʻquv yillari** → **Semestrlar** → har bir semestr uchun **Jarayon muddatlari** ([10-bob](10-terms.md))
9. **Foydalanuvchilar va kirish**: kafedra yordamchisi kabi tashkiliy birlik qamrovini talab qiluvchi rollar uchun endi kafedrani qamrov obyekti sifatida tanlash mumkin ([2-bob](02-users-and-roles.md))

Maʼlumotlar kiritilgach, IT operatoridan jarayon muddatlarini `uv run manage.py term_inspect` bilan tekshirib berishni soʻrang.

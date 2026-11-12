# 9. CSV içe aktarma

Birim, program, bina, derslik ve kod listesi ekranlarının üstündeki **CSV içe aktar** düğmesini kullanın (`Temel verileri CSV dosyasından içe aktarma` yetkisi). Öğrenci kayıtları, öğretim elemanları, dersler ve kayıt kısıtlamaları da aynı şekilde içe aktarılır (aşağıda). Çok büyük dosyalar BT operatörü tarafından `reference_import` komutuyla aynı şekilde içe aktarılabilir.

## Ortak kurallar

- İlk satır sütun adlarını içerir (aşağıdaki tablolar). Kodlama UTF-8'dir; Excel'de "CSV UTF-8" olarak kaydedin.
- Kodu zaten mevcut olan bir satır o kaydı **günceller**. Aynı dosyayı yeniden içe aktarmak mükerrer kayıt oluşturmaz.
- Dile göre sütunlar `sütun_dil` biçimini kullanır: `name_en`, `name_ko`, `name_zh-hans`. Yeni satırlarda İngilizce ad (`name_en`) zorunludur. Boş hücreler mevcut çevirileri silmez.
- Tarihler `2026-03-01` biçiminde; evet/hayır değerleri `1`/`0` veya `true`/`false` olarak yazılır.
- Önce başlık satırı kontrol edilir (zorunlu bir sütun eksikse hiçbir şey içe aktarılmaz). En fazla 500 satırlık dosyalar hemen içe aktarılır; daha büyük dosyalar arka planda (Celery) işlenir. Sonuç, **Temel veriler > CSV içe aktarmaları** altındaki içe aktarma sayfasında görünür (içe aktarılan satırlar, başarısız satırlar ve nedenleri). Başarısız satırlar varsa **Başarısız satırları indir** ile her satır için nedeni içeren bir CSV alırsınız. Bu dosyayı düzeltip yalnızca onu yeniden içe aktarın.
- Sütun adları aşağıdaki tablolarla eşleşmelidir; bilinmeyen sütunlar yok sayılır. Özgün sistemin `name_zh_CN` sütun adı `name_zh-hans` olarak kabul edilir.

## Sütun biçimleri

| Tür | Zorunlu sütunlar | İsteğe bağlı sütunlar |
|---|---|---|
| Birimler | `code`, `type` (birim türü kodu), `name_en`, `effective_start_date` | `parent` (üst birim kodu), `name_ko` vb., `short_name_*`, `effective_end_date`, `sort_order` |
| Programlar | `code`, `org_unit` (birim kodu), `degree_level`, `name_en`, `effective_start_date` | `degree_title_*`, `standard_duration_years`, `effective_end_date`, `allows_second_major`, `allows_minor` |
| Binalar | `code`, `name_en` | `name_*`, `address`, `is_active` |
| Derslikler | `building` (bina kodu), `code` (derslik numarası) | `name_*`, `room_type` (derslik türü kodu), `org_unit`, `capacity`, `is_schedulable`, `is_active` |
| Kod değerleri | `type` (liste kodu), `code`, `name_en` | `name_*`, `sort_order`, `is_active` |

`degree_level` değerleri: `associate`, `bachelor`, `master`, `doctorate`, `certificate`, `non_degree`

Birimlerde üst birimler önce gelmelidir (üniversite → fakülte → bölüm sırasıyla sıralayın).

## Örnek: birimler

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## Öğrenciler ve öğretim elemanları

Öğrenci kayıtları `student_number`, öğretim elemanları `employee_number` ile eşleştirilip güncellenir. Her iki tür de kişi sütunlarını paylaşır.

| Tür | Yeni satırlar için zorunlu sütunlar | İsteğe bağlı sütunlar |
|---|---|---|
| Öğrenci kayıtları | `student_number`, `program` (program kodu), `admission_date`, `family_name` | `catalog_year` (boşsa giriş yılı), `year_level`, `status`, `graduation_date`, `institutional_email` |
| Öğretim elemanları | `employee_number`, `org_unit` (birim kodu), `employment_type`, `family_name` | `academic_title_*`, `hire_date`, `end_date` |
| Kişi sütunları (ortak) | — | `given_name`, `name_ko` gibi dile göre adlar, `birth_date`, `gender`, `email`, `phone`, `national_id` |

- `status` değerleri: `enrolled`, `on_leave`, `withdrawn`, `dismissed`, `graduated` (`graduated` için `graduation_date` zorunludur). İçe aktarmayla değiştirilen bir durum **veri düzeltmesi** olarak değerlendirilir ve durum değişikliği geçmişi oluşturmaz. Gerçek değişiklikler ekranda kaydedilir ([bölüm 13](13-status-changes-and-advisors.md)).
- `employment_type` değerleri: `full_time`, `part_time`, `adjunct`, `visiting`, `emeritus`. `gender` değerleri: `female`, `male`, `other`, `undisclosed`.
- Yeni bir öğrenci kaydının `national_id` değeri mevcut bir kişiyle eşleşirse kayıt o kişiye bağlanır (yeniden kayıt). Aksi hâlde yeni bir kişi oluşturulur. Güncellemede boş hücreler mevcut değerleri silmez.
- İçe aktarılan öğrencilerin ve öğretim elemanlarının hesabı yoktur. Onlara [hesap davetleri](14-merge-and-invitations.md#hesap-davetleri) ile davet gönderin.

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

Ders sürümü içe aktarma [17. bölümde](17-courses-and-curriculum.md), kayıt kısıtlaması içe aktarma [20. bölümde](20-registration.md) açıklanmıştır.

## Kayıt kısıtlamaları

**Ders kaydı > Kısıtlamalar** listesinin üstündeki **CSV içe aktar** (`Kısıtlama koyma ve kaldırma, kural istisnası tanıma` yetkisi) veya `uv run manage.py reference_import registration_holds`. Eski `SRDENY` verilerini veya mali işler biriminin ödeme yapmamış öğrenciler listesini yüklemek için kullanılır.

| Zorunlu sütunlar | İsteğe bağlı sütunlar |
|---|---|
| `student_number`, `hold_type` (`unregistered`, `financial`, `academic`, `administrative`, `other`), `reason` | `starts_at` (varsayılan: içe aktarma zamanı), `ends_at`, `blocks_registration` (varsayılan 1), `blocks_grades`, `blocks_certificates` |

- Her satır yeni bir kısıtlama oluşturur (kaynak `import`). Aynı dosyayı iki kez içe aktarmak kısıtlamaları iki kez oluşturur; bu nedenle yeniden içe aktarmadan önce listeyi kontrol edin.
- Öğrenci numarası bilinmeyen satırlar başarısız olur. Kısıtlamalar ekranda bir gerekçeyle kaldırılır ([bölüm 20](20-registration.md)).
- Zamanlar `2027-03-15` veya `2027-03-15 09:00` biçiminde yazılır (saat dilimi yoksa sunucunun saat dilimi, UTC). `ends_at`, `starts_at` değerinden sonra olmalıdır.

```csv
student_number,hold_type,reason,ends_at
202312345,financial,Tuition unpaid 2027-1,
202254321,academic,Probation meeting needed,2027-03-15
```

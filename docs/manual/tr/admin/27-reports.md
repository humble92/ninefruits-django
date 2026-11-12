# 27. Raporlar ve raporlama görünümleri

Menü: **Raporlar > Raporlar** (`Standart raporları görüntüleme ve indirme` yetkisi). Rol varsayılanları: Öğrenci İşleri, Akademik İşler, Bölüm Sekreteri (kapsam içinde).

## Standart raporlar

Bir rapor ve filtrelerini seçin: ekranda en fazla 500 satır gösterilir ve **CSV indir** tümünü alır (BOM'lu UTF-8, doğrudan Excel'de açılır). İndirmeler `reports.exported` denetim olayına ve `data.exported` güvenlik günlüğü olayına (rapor, süzgeçler, satır sayısı) kaydedilir. `=`, `+`, `-`, `@` (ya da bir sekme veya satır sonu) ile başlayan değerler, Excel'in bunları formül olarak çalıştırmaması için başlarına tek tırnak (`'`) eklenerek dışa aktarılır.

| Rapor | Filtreler | İçerik |
|---|---|---|
| Öğrenci listesi | Birim (altındaki birimler dahil), durum, sınıf düzeyi | Öğrenci numarası, ad, program, birim, sınıf düzeyi, durum, giriş tarihi, mezuniyet tarihi, diploma numarası |
| Birim, program, sınıf ve duruma göre öğrenci sayısı | Birim, durum | Öğrenci sayısı |
| Dönem not özeti | Dönem, akademik durum | Dönem ve genel kredi ile not ortalaması, akademik uyarı sayısı, onur sıralaması ([bölüm 21](21-grades.md)) |
| Mezuniyet adayları | Karşılandı veya karşılanmadı | Öğrenci ve program başına en son mezuniyet denetimi ([bölüm 26](26-graduation.md)) |
| Durum değişiklikleri | Dönem, tarih aralığı | Değişiklik türü, önceki ve sonraki durumlar, geçerlilik tarihi, talep durumu |
| Şube başına kayıtlı öğrenci | Dönem, birim | Şube, öğretim elemanları, kontenjan, kayıtlı, bekleyen |
| Bir dönemde ders kaydı yapmamış öğrenciler | Dönem, birim | O dönemde ders kaydı olmayan kayıtlı öğrenciler |

Görünenler, görüntüleyen kişinin yetki kapsamına (öğrenci kaydı görüntüleme kapsamı vb.) göre belirlenir. Eski sistemin (YUSTIC) ücret ve harç raporları (ödenmemiş harç vb.) kapsam dışıdır ve mevcut değildir.

## reporting görünümleri

Raporlar veritabanındaki `reporting` şemasının görünümlerini okur. BI araçları ve SQL kullanıcıları aynı görünümleri salt okunur `app_reporting` rolüyle sorgular.

| Görünüm | İçerik |
|---|---|
| `reporting.students` | Öğrenci kaydı + kişi adı + program ve birim adları |
| `reporting.headcount` | Birim, program, sınıf düzeyi ve duruma göre öğrenci sayısı |
| `reporting.term_records` | Dönem başına not özeti |
| `reporting.course_grades` | Ders başına notlar (kesinleşmiş olup olmadığı, not, geçti, ders tekrarı) |
| `reporting.section_enrollments` | Şube başına kayıtlı ve bekleyen öğrenciler, öğretim elemanları |
| `reporting.section_meetings` | Ders zamanları ve derslikler |
| `reporting.status_changes` | Durum değişiklikleri |
| `reporting.degree_audits` | Öğrenci ve program türü başına en son mezuniyet denetimi |

- Çevrilmiş sütunlar (`program_name` vb.) oturum yerel ayarına göre belirlenir: `SET app.locale = 'ko';`. Ham jsonb sütunları (`program_name_i18n` vb.) da kullanılabilir.
- Görünümler `security_invoker` olduğundan görüntüleyen kişinin satır düzeyi güvenliği aynen uygulanır. Bir öğrenci hesabıyla okunduğunda yalnızca o öğrencinin satırlarını döndürürler.
- Görünüm tanımları `db/sql/views/reporting.sql` dosyasındadır (özgün `database/sql/views/reporting.sql` değiştirilmeden); bir değişiklikten sonra bir `core` migration'ından yeniden uygulanırlar. Uygulama bunları yönetilmeyen modeller üzerinden okur (`ninefruits.reporting.models`, örn. `ReportStudent`).

Eski `AV_*` görünümleri (yaklaşık 90 adet) kullanılmıyordu ve taşınmadı.

## Bu kurulumun ekranları

- **Raporlar > Raporlar** (`/admin/reports/`): bir rapor seçin ve süzgeçlerini getirmek için **Göster** düğmesine basın (özgün sistem bir rapor seçilir seçilmez süzgeçleri değiştiriyordu). Süzgeçleri doldurup yeniden **Göster** düğmesine basın. Dönem süzgeci olan bir raporda bir dönem seçilene kadar satır yoktur.
- CSV adresi `/reports/{report}.csv?filter=value` şeklindedir (örn. `/reports/students.csv?status=enrolled`). Yalnızca listelenen rapor ve süzgeç adları kabul edilir; sütunlar ve sıralama rapor tanımıyla sabitlenmiştir.
- CSV'deki zamanlar (denetlenme, karar) özgün sistemdeki gibi UTC'de PostgreSQL metni olarak yazılır (`2026-10-24 07:26:59+00`); tarihler `YYYY-MM-DD`, doğru/yanlış `Y`/`N` şeklindedir.
- Şube başına kayıtlı öğrenci raporunun birim süzgeci birim koduna göre süzer (görünümde birim kimliği yoktur). Özgün sistemde bu süzgeci seçmek başarısız oluyordu.
- Şubelerin ve ders zamanlarının satır düzeyi güvenliği yoktur; bu nedenle her şube satırı gösterilir. Kayıtlı ve bekleyen sayıları yalnızca okuyanın görebileceği ders kayıtlarını ve bekleme listesi kayıtlarını sayar.

[Yönetici kılavuzu içindekiler](README.md)

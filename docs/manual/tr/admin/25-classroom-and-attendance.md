# 25. Öğretim elemanı sınıf işlemleri ve devam

Menü: öğretim elemanları portalda **Verdiğim dersler > Sınıf listesi ve devam** (`/portal/sections/{section ID}/attendance/`), öğrenciler portalda **Devam** (`/portal/attendance/`) ekranını kullanır. Personel yönetim panelinde **Müfredat ve şubeler > Şubeler > Değiştir** ekranının **Ders oturumları** sekmesini kullanır.

| Kim | Neler yapabilir |
|---|---|
| Atanmış öğretim elemanları | Sınıf listesi (fotoğraflı) ve CSV, yoklama çizelgesi PDF'i, ders oturumlarını oluşturma, ekleme ve iptal etme, devam bilgisi girme |
| `Şubeleri planlama` yetkisine sahip personel (kapsam içinde) | Öğretim elemanlarıyla aynı + yönetim panelinde ders oturumları |
| `Şubeleri görüntüleme` yetkisine sahip personel (kapsam içinde) | Sınıf listesi, yoklama çizelgesi, devam bilgisini görüntüleme |
| Öğrenciler | Kendi devam durumları |

Duyurular, ödevler ve ders materyalleri gibi sınıf özellikleri LMS'e bırakılmıştır (taşıma planı bölüm 12).

## Eski sistemden farklar

- **Eski sistem (YUSTIC) devam bilgisini kaydetmiyordu.** "Yoklama çizelgesi", sınıf listesinin yanına tarih ve toplam olmadan boş kutular (nüshaya göre değişen 27 ila 34 adet) basan bir PDF'ti. Yeni sistem ders zamanlarından **ders oturumları** oluşturur, her oturum için var, geç, yok veya mazeretli bilgisini kaydeder ve kayıtları ile toplamları yoklama çizelgesi PDF'ine basar.
- **Sınıf listesi.** Eski öğretim elemanı ekranı yalnızca öğrenci numaralarını ve adları gösteriyordu (açılır pencerede kimlik numarasını ve adresi açığa çıkarıyordu) ve Excel indirme seçeneği yoktu. Yeni sistem yalnızca öğrenci numarası, ad, fotoğraf, program, sınıf düzeyi ve iletişim e-postasını gösterir ve CSV olarak indirilir. İndirmeler denetim günlüğüne kaydedilir.
- **Öğretim elemanlarının öğrencilerine erişimi.** Öğretim elemanlarının şubelerindeki öğrencilerin öğrenci kayıtlarını ve kişi bilgilerini görmesine bir satır düzeyi güvenlik politikası (`student_records_instructor_select`, `util.taught_student_record_ids()` işlevi) izin verir ve uygulamanın görünürlük kuralları da buna uyar (önceden özgün sistem yalnızca danışmanlık öğrencilerini gösteriyordu; bu yüzden not girişi ekranında bile adlar boş kalıyordu).

## Ders oturumları

- **Oluşturma**: haftalık ders zamanlarının (gün, saat, ders saati) her tekrarı için bir oturum. Öğretim elemanları **Ders zamanlarından oluştur** düğmesini; personel **Ders oturumları** sekmesinin üstündeki **Oturumları oluştur** düğmesini (bir onay sayfasıyla) veya `uv run manage.py attendance_generate_sessions {term}` komutunu (tüm dönem) kullanır. Mevcut oturumlara ve devam bilgilerine dokunulmaz, bu nedenle ders zamanları değiştikten sonra yeniden çalıştırılabilir. İptal edilmiş şubeler atlanır.
- **Oturum ekle**: telafi dersi gibi ders zamanları dışındaki bir ders (tarih, başlangıç, bitiş). Yalnızca alt dönem içindeki tarihler ve tarih ile başlangıç saati başına yalnızca bir oturum.
- **İptal et**: oturumu gerekçeyle iptal edin. Oturum kalır ancak toplamların dışında tutulur. **Geri al** onu geri getirir.
- Tatil takvimi yoktur. Resmî tatillerdeki oturumları iptal edin (bir dönem takvimi eklendiğinde oluşturucu bunları dışarıda bırakabilir).

## Devam bilgisi girme

Oturumun **Devam** ekranında her öğrenci için var, geç, yok veya mazeretli seçin bir not ekleyin (200 karakter) ve **Devamı kaydet** düğmesine basın. En hızlı yol **Hepsi var** (kaydetmeden herkesi var olarak işaretler) seçip ardından istisnaları değiştirmektir.

- Devam bilgisi oturum gününden itibaren girilebilir (gelecekteki veya iptal edilmiş oturumlar için girilemez).
- Yeniden kaydetmek yalnızca değişen öğrencileri kaydeder ve denetim olayı (`attendance.recorded`) öğrenci başına eski ve yeni değeri saklar.
- Durumu temizlemek öğrenciyi yeniden "kaydedilmedi" durumuna getirir.
- Yalnızca kayıtlı ve dersi tamamlamış öğrenciler kaydedilebilir (bırakan ve dersten çekilen öğrenciler sınıf listesinde yer almaz).

## Toplamlar

| Öğe | Tanım |
|---|---|
| Yapılan oturumlar | İptal edilmemiş ve bugün veya öncesine denk gelen oturumlar |
| Devam oranı | (var + geç + mazeretli) ÷ yapılan oturumlar × 100, bir ondalık basamak (yarımlar yukarı yuvarlanır) |
| Kaydedilmedi | Kaydı olmayan yapılmış oturumlar |

Belirli sayıda geç kalmayı devamsızlığa çeviren veya üçte birin üzerindeki devamsızlıkta F veren bir kural yoktur. Bu, üniversiteden üniversiteye değiştiği için öğretim elemanları devamı nota kendileri yansıtır. Sayım kuralları tek bir hizmette (`AttendanceSummary`) bulunur; bu nedenle sınıf listesi, yoklama çizelgesi ve öğrenci sayfası aynı sayıları gösterir.

## Yoklama çizelgesi PDF'i ve sınıf listesi CSV'si

Her iki indirme de denetim günlüğüne kaydedilir (`attendance.sheet_exported`, `attendance.roster_exported`). `=`, `+`, `-` veya `@` (ya da bir sekme veya satır sonu) ile başlayan CSV değerleri formül olarak çalıştırılmamaları için başlarına tek tırnak eklenerek dışa aktarılır.

- **Yoklama çizelgesi (PDF)** (`/sections/{section ID}/attendance-sheet`): yatay A4. Öğrenciler satırlarda, oturumlar sütunlarda (iptal edilenler hariç), öğrenci başına O/△/X/E işaretleri ve toplamlar. Henüz yapılmamış oturumlar boştur, bu nedenle elle kayıt için de kullanılabilir. PDF sunucusu (Gotenberg) yanıt vermediğinde "PDF oluşturulamadı" gösterilir.
- **Sınıf listesi (CSV)** (`/sections/{section ID}/roster.csv`): öğrenci numarası, ad, program, sınıf düzeyi, iletişim e-postası, kayıt durumu. BOM'lu UTF-8, bu nedenle doğrudan Excel'de açılır.

## Öğrenci portalı

**Devam**: dönem (varsayılan olarak başlamış en son dönem) ve ders başına var, geç, yok ve mazeretli sayıları ve devam oranı; genişletildiğinde yapılan her oturumun kaydı (yalnızca öğretim elemanının girdikleri, aksi hâlde "Kaydedilmedi").

## İşletim prosedürü

1. Dönem başlamadan önce şubelerin ders zamanlarını kesinleştirin ([bölüm 18](18-sections-and-timetables.md)).
2. Oturumları `uv run manage.py attendance_generate_sessions {term} --actor=...` ile oluşturun (öğretim elemanları da ekranda oluşturabilir). Yalnızca bir şube: `--section=CSE2010-01`; yalnızca şube sayısı: `--dry-run` ([işletim komutları](../operations/commands.md)).
3. Ders zamanları değiştiğinde yeniden çalıştırın. Kaldırılan zamanların oturumları otomatik olarak silinmez; bunları iptal edin.

## Bu kurulumdaki ekranlar

Ekranlar ve özellikler özgün sistemdekilerle (Filament, Livewire) aynıdır; bazı denetimler biraz farklı çalışır.

- Yönetim panelindeki şube değiştirme ekranının **Ders oturumları** sekmesi: tarih, saat, derslik, durum, girilen kayıtlar, gerekçe. Bir satırın **İptal et** bağlantısı gerekçe için bir sayfa, **Geri al** bir onay sayfası açar. **Oturumları oluştur**, ekranın üstündeki bir işlem düğmesidir. Yalnızca `Şubeleri görüntüleme` yetkisi olan personel sekmeyi düğmeler olmadan görür.
- Öğretim elemanı portalında **İptal et**, oturum satırında bir gerekçe alanı açar; gerekçeyi girip yeniden **İptal et** düğmesine basın (özgün sistemdeki tarayıcı istemi yerine).
- **Devam** giriş sayfası `?meeting={meeting ID}` ile biter, bu nedenle yer imlerine eklenebilir. **Geri** sınıf listesine ve oturum listesine döner.
- Satır düzeyi güvenlik altında sınıf listesi yalnızca ders kayıtlarını ve öğrenci kayıtlarını görebilen kişiler için doldurulur. Varsayılan roller (Akademik İşler, Bölüm Sekreteri) `Ders kayıtlarını ve sınıf listelerini görüntüleme` ve `Öğrenci kayıtlarını görüntüleme` yetkilerine de sahiptir. Yalnızca `Şubeleri planlama` verilmiş bir rol boş bir sınıf listesi ve çizelge görür (özgün sistemdeki gibi).

[Yönetici kılavuzu içindekiler](README.md)

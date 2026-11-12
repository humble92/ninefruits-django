# 18. Şubeler ve ders programları

Menü: **Müfredat ve şubeler > Şubeler**, **Ders programları** (`Şubeleri görüntüleme`, `Şubeleri planlama (öğretim elemanları, saatler, derslikler)` yetkileri. Bir birim kapsamıyla atandıklarında yalnızca o birimin açtığı şubeleri kapsarlar)

## Şube oluşturma

1. **Şubeler > Oluştur** altında dönemin alt dönemini, dersi, şube numarasını (örn. `01`), kontenjanı ve açan birimi girin. Ders adı ve kredi, alt dönemin başlangıç tarihinde geçerli olan ders sürümünden gelir.
2. Düzenleme ekranının sekmelerinde **Ders zamanları**, **Öğretim elemanları** ve **Ayrılmış kontenjanlar** bilgilerini girin.
3. Her şey hazır olduğunda **Yayımla** düğmesine basın. Yalnızca yayımlanmış şubeler portaldaki **Ders kataloğu**nda görünür ve ders kaydına açılır ([bölüm 20](20-registration.md)).

| Durum | Anlamı |
|---|---|
| Taslak | Planlanıyor. Yalnızca personel ve atanmış öğretim elemanları görür |
| Yayımlandı | Öğrencilere görünür. **Taslağa geri al** ile taslağa döndürülebilir |
| İptal edildi | Gerekçe zorunludur. Derslik ve öğretim elemanı saatleri boşa çıkar. **Yeniden aç** şubeyi tekrar taslağa çevirir; bu arada başka bir şube o saati almışsa yeniden açılamaz |

Yalnızca taslak şubeler silinebilir. Yayımlanmış bir şube silinmez, iptal edilir.

| Alan | Açıklama |
|---|---|
| Alt dönem | Dönemin bir alt dönemi ([bölüm 10](10-terms.md)). Başka bir alt döneme taşımak, ders tarihlerini ve ders sürümünü o alt döneme göre değiştirir |
| Kimler kayıt olabilir, Kimler kayıt olamaz | Sınıf düzeyi, giriş yılı, program, birim. Örnek: dersin kendi ana dal öğrencilerini bir genel eğitim dersinden hariç tutmak. Çift ana dal ve yan dal öğrencileri de o programın öğrencisi sayılır |
| Öğretim dili | örn. `ko`, `en` |
| Bekleme listesi büyüklüğü | Şube dolduğunda kabul edilen bekleme listesi kaydı sayısı. 0: bekleme listesi yok ([bölüm 20](20-registration.md)) |
| Değerlendirme (değerlendirme yöntemi) | Mutlak değerlendirme (varsayılan; öğretim elemanı puanları girer ve notlar bunlardan hesaplanır) veya bağıl değerlendirme (yalnızca notlar girilir, not üst sınırları uygulanır). Öğretim elemanı değişikliği not girişi ekranından talep eder ve şubenin personeli onaylar. Notlar girildikten sonra değiştirilemez ([bölüm 21](21-grades.md)). Dönem kopyalanırken birlikte kopyalanır |

## Ders zamanları ve derslikler

**Ders zamanları** sekmesinde günü, başlangıç ve bitiş saatini ve dersliği girin. Bir **Ders saati** seçmek saatleri doldurur. Alt dönemin tarihlerini kullanmak için ders tarihlerini boş bırakın.

- İki şube aynı dersliği aynı saatte kullanamaz ve bir öğretim elemanı aynı saatte iki şubede ders veremez. Bunu veritabanı zorunlu kılar; ekran çakışan şubeyi gösterir, örn. "Derslik bu saatte OOO tarafından zaten ayrılmış".
- Bir dönemin ilk ve ikinci yarısı gibi tarihler çakışmadığında aynı saat ve derslik kullanılabilir.
- İptal edilmiş şubeler hiçbir saati işgal etmez.

## Öğretim elemanları

**Öğretim elemanları** sekmesinde öğretim elemanlarını bir rolle (Öğretim elemanı, Ortak öğretim elemanı, Ders asistanı) atayın. Bir şubenin birden fazla öğretim elemanı olabilir. Aynı saatte başka bir şubede ders veren bir öğretim elemanı atanamaz. Öğretim elemanları ders programını ve ders izlencesini portalda **Verdiğim dersler** altında yönetir.

## Ayrılmış kontenjanlar

**Ayrılmış kontenjanlar** sekmesinde öğrenci grupları için kontenjan ayırın (örn. programın ana dal öğrencileri için 30 kişilik kontenjan). **Herkese açılma zamanı** geçtikten sonra kullanılmayan kontenjanı herkes alabilir. Ayrılmış kontenjanların toplamı kontenjanı aşamaz. Ders kaydı sırasında uygulanırlar ([bölüm 20](20-registration.md)).

## Ders izlencesi

Öğretim elemanı izlenceyi portalda **Verdiğim dersler** altında yazar (şube ekranındaki **Ders izlencesi** düğmesinden de açılır). Genel bakışı, öğrenme hedeflerini, ders kitapları ve materyalleri, ders kurallarını, değerlendirmeyi (ölçütler ve ağırlıklar) ve haftalık planı girer; **Yayımlandı** olduğunda öğrenciler görebilir.

## Başka bir dönemden kopyalama

Şube listesindeki **Başka bir dönemden kopyala**, önceki bir dönemin (genellikle geçen yılın aynı dönemi) planından başlar. Sonucu önce **Yalnızca önizleme** ile kontrol edin.

- İptal edilmemiş ve kapsamınızdaki şubeler taslak olarak kopyalanır.
- Birlikte kopyalananlar: hâlâ görevde olan öğretim elemanları, ders zamanları ve derslikler, ayrılmış kontenjanlar (açılma zamanı dönemlerin başlangıç tarihleri arasındaki fark kadar kaydırılır), ders izlencesi (yayımlanmamış taslak olarak).
- Alt dönemler koda göre eşleştirilir (yoksa tam dönem). Ders sürümü yeni alt dönemin başlangıç tarihine göre alınır.
- Şube numarası hedef dönemde zaten bulunan şubeler atlanır; bir derslik zaten doluysa şube dersliksiz kopyalanır. Sonuç bildirimi atlanan şubeleri ve kontrol gerektirenleri listeler.

BT operatörleri aynı işlemi `uv run manage.py section_copy` ile yapabilir.

## Ders programları ve kontroller

- **Ders programları**: haftalık ders programını görmek için bir dönem ve bir derslik veya öğretim elemanı seçin.
- Yayımlamadan önce kontrol: BT operatörü kontenjandan küçük derslikleri, emekli olmuş öğretim elemanlarını, ders sürümü uyuşmazlıklarını ve kontenjanı aşan ayrılmış kontenjanları bulmak için `uv run manage.py schedule_check_conflicts <term code>` komutunu çalıştırır ([komut başvurusu](../operations/commands.md#schedule_check_conflicts)).

## Kapsam

Liste ve ekranlar yalnızca `Şubeleri görüntüleme` ve `Şubeleri planlama (öğretim elemanları, saatler, derslikler)` kapsamlarındaki açan birimlerin şubelerini gösterir. Ders zamanları, öğretim elemanları ve ayrılmış kontenjanlar sekmeleri ile durum düğmeleri (Yayımla, Taslağa geri al, Şubeyi iptal et, Yeniden aç), şubenin açan birimini kapsayan bir kapsamda `Şubeleri planlama (öğretim elemanları, saatler, derslikler)` yetkisi gerektirir. Ders programı sayfası devam eden dönemle (yoksa bir sonrakiyle) açılır. Telefonlarda hafta günü başına bir liste gösterir.

[Yönetici kılavuzu içindekiler](README.md)

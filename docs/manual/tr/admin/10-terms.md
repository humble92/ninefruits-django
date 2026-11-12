# 10. Akademik yıllar, dönemler, işlem aralıkları

Menü: **Temel veriler > Akademik yıllar**, **Dönem türleri**, **Dönemler**, **Ders saatleri** (`Akademik yılları, dönemleri, dönem türlerini ve ders saatlerini yönetme` yetkisi; işlem aralıkları için `İşlem aralıklarını yönetme` gerekir)

## Eski sistemden farklar

Eski sistem (YUSTIC) "geçerli dönemi" tek bir dönem durumu işaretiyle (`AFS_CHECK`) belirliyordu; bu da geçen dönemin notlarıyla gelecek dönemin ders kaydını aynı anda yürütmeyi zorlaştırıyordu. Yeni sistemde "geçerli dönem" ayarı yoktur. Bunun yerine her iş, hangi dönemin geçerli olduğuna karar vermek için açık **işlem aralıklarına** bakar. Önceki dönemin not girişi, içinde bulunulan dönemin dersleri ve gelecek dönemin ders kaydı birbirini engellemez.

## Akademik yıllar ve dönemler

1. **Akademik yıllar**: kod (örneğin `2026`), ad, başlangıç/bitiş tarihleri. Akademik yıllar çakışamaz.
2. **Dönem türleri**: birinci dönem, ikinci dönem, yaz/kış yoğunlaştırılmış dönemleri vb. **Normal dönem** işareti daha sonra kredi sınırları gibi kurallarda kullanılır.
3. **Dönemler**: akademik yıl, dönem türü, kod (örneğin `2026-FA`, yalnızca gösterim için), ad, derslerin başlangıç/bitiş tarihleri. Aynı türdeki dönemlerin ders süreleri çakışamaz.

## Dönem durumu

| Durum | Anlamı | İşlem aralıkları |
|---|---|---|
| Planlandı | Hazırlık aşamasında. Öğrenciler göremez | Açılmaz |
| Yayımlandı | Yürürlükte | Açılır |
| Notlar kapatıldı | Notlar kesinleştirildikten sonra | Açılır (nota itiraz vb.) |
| Arşivlendi | Tamamlandı | Açılmaz |

Durum yalnızca dönemin **Düzenle** sayfasındaki **Durumu değiştir** ile değişir. Sıra Planlandı → Yayımlandı → Notlar kapatıldı → Arşivlendi şeklindedir; Yayımlandı ve Notlar kapatıldı durumları bir adım geri alınabilir. Değişiklikler bir gerekçeyle kaydedilir.

## Alt dönemler

Alt dönem, bir dönem içinde derslerin yürütüldüğü bir süredir. Alt dönemleri dönemin **Düzenle** sayfasındaki **Alt dönemler** sekmesinde yönetin.

- Bir dönem oluşturulduğunda **Tam dönem** alt dönemi (kod `FULL`) otomatik olarak oluşturulur; dönem tarihleri değiştiğinde onları izler.
- Bazı dersler dönemin yalnızca bir bölümünde yürütüldüğünde, örneğin ilk yarı ve ikinci yarı 8 haftalık dersler veya 3 haftalık yoğunlaştırılmış bir ders için alt dönem ekleyin. Örnek: `A` ilk yarı 1/9–25/10, `B` ikinci yarı 26/10–20/12, `I` yoğunlaştırılmış 1/11–21/11.
- Alt dönemler dönemin içinde yer almalıdır. Dönemi kısaltırsanız önce dışarıda kalacak alt dönemleri düzeltin.
- Her şube bir alt döneme bağlıdır ([bölüm 18](18-sections-and-timetables.md)). Alt dönem kullanmayan bir üniversitenin yalnızca tam dönem alt dönemine ihtiyacı vardır.

## İşlem aralıkları

İşlem aralıklarını dönemin **Düzenle** sayfasının altındaki **İşlem aralıkları** bölümüne ekleyin.

| Alan | Açıklama |
|---|---|
| İşlem aralığı | Ders sepeti, Ders kaydı, Ekle/bırak, Dersten çekilme, Not girişi, Nota itiraz, Ders değerlendirme, Mezuniyet başvurusu, Çift ana dal ve yan dal başvuruları |
| Alt dönem | Yalnızca derse bağlı işlem aralıkları için (ekle/bırak, dersten çekilme, not girişi, nota itiraz, ders değerlendirme). Varsayılan, tam dönem alt dönemidir |
| Açılış, Kapanış | Kurumun saat dilimindeki zamanlar. İşlem aralığı kapanış zamanında kapanır |
| Uygunluk | Boşsa herkes. Sınıfları, bir giriş yılı aralığını, programları ve birimleri (alt birimler dahil) birleştirin. Bir öğrencinin tüm koşulları sağlaması gerekir |

İki tür işlem aralığı vardır.

| Tür | İşlem aralıkları | Esas alınan |
|---|---|---|
| Derse bağlı işlem aralıkları | Ekle/bırak, Dersten çekilme, Not girişi, Nota itiraz, Ders değerlendirme | Dersin bağlı olduğu alt dönem. İkinci yarı dersi, ikinci yarı alt döneminin ekle/bırak, dersten çekilme ve not girişi aralıklarını izler |
| Öğrenci/dönem işlem aralıkları | Ders sepeti, Ders kaydı, Mezuniyet başvurusu, Çift ana dal ve yan dal başvuruları | Dönemin tamamı. Alt dönem yoktur |

**Alt döneme göre işlem aralığı oluşturma**: Alt dönemler sekmesinde, başka bir alt dönemin (genellikle tam dönem) ders işlem aralıklarını bu alt dönemin tarihlerine kaydırarak kopyalamak için bir alt dönemde **İşlem aralıklarını kopyala** düğmesine basın. Erken işlem aralıkları (ekle/bırak, dersten çekilme) alt dönem başlangıcına olan uzaklıklarını; geç işlem aralıkları (not girişi, ders değerlendirme) alt dönem bitişine olan uzaklıklarını korur. Kopyaladıktan sonra kontrol edip düzenleyin.

**Kademeli açılış örneği**: üç ders kaydı işlem aralığı oluşturun.

| İşlem aralığı | Açılış | Uygunluk |
|---|---|---|
| Ders kaydı | 10 Şubat 10:00 | 4. sınıf |
| Ders kaydı | 11 Şubat 10:00 | 3. sınıf |
| Ders kaydı | 12 Şubat 10:00 | 1. ve 2. sınıflar |

Her öğrencinin sınıfı ve giriş yılı, öğrenci kaydı verilerinden gelir ([12. bölüm](12-people-and-student-records.md)).

## Ders saatleri

Ders zamanının birimi. Kodu (örneğin `1`), adı (1. ders saati), başlangıç/bitiş saatlerini ve günleri ayarlayın. Bir şubenin ders zamanı girilirken bir ders saati seçildiğinde başlangıç ve bitiş saatleri otomatik doldurulur. Kore üniversitesi profili 09:00'dan başlayan on adet 50 dakikalık ders saati yükler (Pazartesi–Cuma).

Ders saati zamanları saat diliminden bağımsız "duvar saati" zamanlarıdır; tam girildiği gibi kaydedilir.

İşlem aralıklarının açılış ve kapanış zamanları yönetim panelinde kurumun saat diliminde girilir ve gösterilir, UTC olarak saklanır.

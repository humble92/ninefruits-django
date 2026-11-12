# 28. LMS entegrasyonu

Menü: yönetim panelinde **LMS entegrasyonu > LMS platformları**, **Ders bağlantıları**, **Eşitleme günlükleri** (`LMS platformlarını, bağlantıları ve eşitlemeyi yönetme` yetkisi; varsayılan: Sistem Yöneticisi, Akademik İşler). Öğretim elemanları portaldaki **Verdiğim dersler** altındaki ve şube ayrıntısındaki LMS bağlantılarını ve not girişi ekranındaki **Puanları LMS üzerinden yükle** düğmesini kullanır. Yükleme, not girişiyle aynı koşullara tabidir (atanmış öğretim elemanı, not girişi aralığı içinde).

Geliştirici ayrıntıları (bağlayıcı yazma, API) [LMS entegrasyon kılavuzunda](../../../lms-integration-guide.md) yer alır.

## Ne nereye gider

| SIS → LMS | Ne zaman |
|---|---|
| Şube (ders oluşturma) + öğretim elemanları | Şube **yayımlandığında** ve `lms_sync` ile |
| Onaylanmış ders kaydı → derse kayıt | Ders kaydında, bekleme listesinden kayda almada veya personel ders kaydında hemen |
| Bırakma veya dersten çekilme → kayıt silme | Hemen |
| Tam mutabakat | Her gün 02:30'da (`lms_reconcile`, zamanlanmış görev `lms.reconcile`) |

| LMS → SIS | Ne zaman |
|---|---|
| Son puanlar (taslak) | Öğretim elemanı not girişi ekranında **Puanları LMS üzerinden yükle** düğmesine tıkladığında. Kaydetme ve gönderme öğretim elemanı tarafından yapılır |

Kesinleşmiş notlar LMS'e gönderilmez. Ders materyalleri, ödevler ve kısa sınavlar LMS'te bulunur.

## Platformlar

**LMS platformları**: kod, ad (dil başına), sürücü, temel URL, kimlik bilgileri, etkin, sınıf listelerini eşitle, son puanları çek.

- **Yok (yalnızca kayıt)** sürücüsü: hiçbir şey çağırmaz ve gönderilecek olanı kaydeder. Entegrasyondan önce akışı kontrol etmek veya tanıtım için kullanın. Demo verilerindeki `DEMO` platformu bunu kullanır.
- `Moodle`, `Open edX`: henüz bağlayıcı yok ("henüz uygulanmadı" olarak işaretli). Seçildiğinde eşitlemeler başarısız olarak kaydedilir.
- **Kimlik bilgileri** her satıra bir `key=value` olacak şekilde yazılır (örn. `token=...`). Şifrelenmiş olarak saklanır ve hiçbir zaman geri gösterilmez. Düzenlemede alanı boş bırakmak saklanan değerleri korur. Veri değişikliği geçmişi de değerleri tutmaz.
- **Etkin** açıldığında bundan sonra şube yayımlamaları ve ders kaydı değişiklikleri hemen aktarılır ve platform gece mutabakatına dahil edilir.

## Ders bağlantıları ve eşitleme günlükleri

- **Ders bağlantıları**: hangi şubenin hangi platform dersine (kimlik, URL) bağlı olduğu, durum (Beklemede/Bağlandı/Başarısız), son eşitleme ve hata. Platform, durum ve döneme göre süzgeçler; ders koduna göre arama. Satır işlemi **Yeniden eşitle** (bir onay sayfasıyla) şubeyi, öğretim elemanlarını ve sınıf listesini yeniden gönderir.
- **Eşitleme günlükleri**: adım başına sonuç ve mesaj (ders, üye ekleme ve çıkarma, puanları çekme, teslim edilen puanlar, mutabakat). Bir hatanın nedenini burada arayın. Bir satırı açmak başlangıç ve bitiş zamanlarını ve içeriği (payload) gösterir.
- Komutlar: `uv run manage.py lms_sync {platform} --term={term}` (tam gönderim, `--dry-run`), `uv run manage.py lms_reconcile` (mutabakat). Bkz. [işletim komutları](../operations/commands.md#lms-entegrasyonu-aşama-12).

## Portal

- Platform ders bağlantısı, öğrenciler ve öğretim elemanları için ders ayrıntısında ve öğretim elemanının **Verdiğim dersler** listesinde gösterilir (**LMS** sütunu; yalnızca bağlı şubeler).
- Not girişi: platformda **Son puanları çek** açık ve şube bağlıysa **Puanları LMS üzerinden yükle** düğmesi görünür. Yalnızca puan sütununu doldurur ve kaydetmez.

## Entegrasyon API'si

Bir API (`/api/v1/lms/platforms/...`), sonuçları sonradan bildiren veya puanlarını kendileri gönderen platformlara hizmet eder. Yalnızca `LMS platformlarını, bağlantıları ve eşitlemeyi yönetme` yetkisine sahip ayrı bir entegrasyon hesabı oluşturun; bir operatör onun belirtecini `uv run manage.py api_issue_token {email} --days=365` ile düzenler ve platformun yöneticisine iletir. Belirteç yalnızca bir kez, düzenlendiğinde gösterilir. `api_revoke_tokens` onu iptal eder. Düzenleme ve iptal denetim günlüğüne kaydedilir.

- Puan teslimi (`.../scores/`) ile alınan puanlar da kaydedilmez. Öğretim elemanı **Puanları LMS üzerinden yükle** düğmesine tıkladığında alınan en son puanlar formu taslak olarak doldurur.
- Eşitleme sonuçları (`.../sync-results/`) **Eşitleme günlükleri** içinde saklanır ve ders sonuçları **Ders bağlantıları** içindeki durumu değiştirir.

## Sık sorulan sorular

- **Bir öğrenci LMS'te eksik.** Eşitlenebilmesi için öğrencinin bir hesabı (kullanıcı) olması gerekir. Hesabı yoksa davet edin ([bölüm 14](14-merge-and-invitations.md)); bir sonraki mutabakat onu ekler.
- **Bir eşitleme başarısız durumda kalıyor.** Eşitleme günlüğündeki mesajı okuyun. Süresi dolmuş kimlik bilgileri yaygın bir nedendir. Platformun düzenleme ekranındaki değerleri değiştirin ve **Yeniden eşitle** işlemini yapın.
- **Platform değiştirdik.** Yeni platformu oluşturun ve eskisinin Etkin ayarını kapatın. Bağlantılar her platform için ayrı oluşturulur.

## Bu kurulumdaki ekranlar

Ekranlar ve özellikler özgün sistemdekilerle (Filament, Livewire) aynıdır; bazı etkileşimler farklıdır.

- Kimlik bilgileri, özgün sistemdeki anahtar/değer tablosu yerine bir metin alanına `key=value` satırları olarak girilir. Hatalı satırlar satır numaralarıyla reddedilir.
- Bir platformun **seçeneklerinin** (platform başına rol kimlikleri vb.) ekranda bir alanı yoktur. Geliştiriciler bunları bir bağlayıcı gerektirdiğinde ayarlar ([entegrasyon kılavuzu](../../../lms-integration-guide.md) bölüm 3).
- **Yeniden eşitle** bir onay sayfasından geçer. Bağlayıcı hataları (bağlayıcısı olmayan bir sürücü, bir platform kesintisi) "Eşitleme başarısız: ..." mesajı olarak görünür ve ders bağlantısı Başarısız olur (özgün sistem bir hata sayfası gösteriyordu).
- Eşitleme günlükleri salt okunurdur. Bir satırı açmak içeriği JSON olarak gösterir.
- Not girişi ekranındaki **Puanları LMS üzerinden yükle**, tablonun altındaki düğme satırındadır. Sayfayı yalnızca puan alanları değiştirilmiş olarak, zaten yazılmış olanları koruyarak yeniden gösterir. **Taslağı kaydet** düğmesine basılana kadar hiçbir şey kaydedilmez.
- Entegrasyon API'si ve belirteç komutları (`api_issue_token`, `api_revoke_tokens`) bu kurulumda yenidir (özgün sistemde API yoktu).

[Yönetici kılavuzu içindekiler](README.md)

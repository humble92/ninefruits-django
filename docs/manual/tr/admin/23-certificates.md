# 23. Belgeler

Menü: **Belgeler > Düzenlenen belgeler**, **Belgeler > Belge türleri**, **Ayarlar > Belge ayarları**. Belgeler, öğrenci kaydı ekranındaki **Belge düzenle** düğmesiyle düzenlenir (**Öğrenciler ve personel > Öğrenci kayıtları**, bir kaydı açın). Öğrenciler kendi belge PDF'lerini portalda **Belgeler** altından indirir. Herkes bir belgeyi `/verify/{code}/` sayfasında doğrulayabilir.

| Yetki | Neye izin verir |
|---|---|
| `Belge düzenleme, yeniden oluşturma ve iptal etme` | Düzenleme, yeniden oluşturma, iptal etme, düzenlenen belgeleri görüntüleme (öğrenci kaydı görüntüleme kapsamı içinde) |
| `Belge türlerini, şablonlarını ve ayarlarını yönetme` | Türler ve dil başına şablonları, seri numarası biçimi, imzalayanlar |

Rol varsayılanları: Belge Sorumlusu belge düzenler, Öğrenci İşleri her ikisine sahiptir, Akademik İşler türleri ve şablonları yönetir. Düzenleme yetkisini **genel kapsamla** verin (veritabanı politikası yalnızca genel bir yetkiyi kabul eder); bir personelin hangi öğrenciler için belge düzenleyebileceği, öğrenci kaydı görüntüleme kapsamına göre belirlenir. Örneğin bir fakültenin belge sorumlusuna `Belge düzenleme, yeniden oluşturma ve iptal etme` yetkisini genel olarak, `Öğrenci kayıtlarını görüntüleme` yetkisini o fakülte için verin.

## Eski sistemden farklar

- **Düzenlenen belgeler kaydı.** Eski sistem (YUSTIC) doğrudan ekrandan yazdırıyordu (`aca3/cti_*`) ve kaydı (`SRCERT`) yalnızca numara üretmek için vardı; bu nedenle bir belgeyi kimin düzenlediğini veya iptal edilip edilmediğini göstermiyordu. Yeni sistem her düzenleme için seri numarasını, doğrulama kodunu, personeli, kullanım amacını, nüsha sayısını, PDF dosyasını ve sağlama toplamını kaydeder; iptal edilen bir belge satırını korur.
- **Doğrulama.** Eski sistemde yoktu. Her belge bir doğrulama kodu ve QR kodu taşır; herkese açık bir sayfa belgenin düzenlendiğini, türünü, düzenlenme tarihini ve maskelenmiş belge sahibini (adın ilk ve son karakteri, öğrenci numarasının ilk 4 karakteri) gösterir.
- **Şablonlar.** Eski sistemde her tür ve dil için ayrı bir PDF betiği vardı. Yeni sistem her tür için dil başına bir şablonu (başlık, metin, alt bilgi, imzalayan) ekranda düzenler.
- **Engeller.** Eski sistem belgeleri ders kaydı engeli listesinden bağımsız olarak düzenliyordu. Yeni sistem belge engeli olan bir öğrenciye belge düzenlemez ([bölüm 20](20-registration.md)).
- Ücretler kaydedilmez (eski sistem yalnızca tutarı kaydediyordu).
- Öğrencilerin çevrim içi talebi yoktur (taşıma planı 17.5). Belgeleri personel düzenler.

## Türler ve şablonlar

**Belge türleri**: kod (seri numarasında kullanılır), ad (dil başına), kimler için (tüm öğrenci kayıtları / öğrenciler (mezun olmayan) / mezunlar), notları içerir, fotoğraf içerir, etkin, sıra. Kore üniversite profili (`setup_install --profile=korean-university`) üç türü dört dilde (Korece, İngilizce, Basitleştirilmiş Çince, Laoca) şablonlarıyla birlikte hazır olarak yükler. Herhangi bir tür varsa hiçbir şey eklemez; bu nedenle düzenlemeleriniz korunur.

| Kod | Tür | Kimler için | Not |
|---|---|---|---|
| `ENR` | Öğrenci belgesi | Öğrenciler (mezun olmayan) | |
| `GRD` | Mezuniyet belgesi | Mezunlar | Mezuniyet tarihi, diploma numarası |
| `TRN` | Akademik transkript | Tüm öğrenci kayıtları | Döneme göre kesinleşmiş notlar tablosu, genel not ortalaması ve kazanılan kredi |

**Şablonlar** (tür düzenleme ekranının altındaki **Şablonlar** bölümü): dil başına bir tane. Dil, başlık, metin (paragraflar boş bir satırla ayrılır), alt bilgi, imzalayan. Metin süslü parantez içinde yer tutucular kullanır.

| Yer tutucu | Değer |
|---|---|
| `{institution}` | Kurum adı (o dilde) |
| `{student_name}`, `{student_number}` | Ad (o dildeki biçimiyle, yoksa Latin yazımıyla), öğrenci numarası |
| `{program}`, `{org_unit}` | Program, birim |
| `{admission_date}`, `{graduation_date}`, `{degree_number}` | Giriş tarihi, mezuniyet tarihi, diploma numarası |
| `{status}`, `{year_level}` | Öğrenci durumu, sınıf düzeyi |
| `{birth_date}`, `{gender}`, `{nationality}` | Doğum tarihi, cinsiyet, uyruk |
| `{issue_date}`, `{serial_number}`, `{purpose}`, `{copies}` | Düzenlenme tarihi, seri numarası, kullanım amacı, nüsha sayısı |

Tarihler o dilin biçiminde yazdırılır (örn. `October 24, 2026`, `2026년 10월 24일`). Eksik bir değer (örn. mezuniyet tarihi) boş olarak yazdırılır; listede olmayan bir yer tutucu yazıldığı gibi kalır. Metnin üstüne otomatik olarak bir kişisel bilgiler tablosu eklenir (ad, öğrenci numarası, doğum tarihi, cinsiyet, uyruk, program, giriş tarihi; ardından mezunlar için mezuniyet tarihi, diğerleri için durum ve sınıf düzeyi). Belgenin tamamı (tablo etiketleri, tarihler, durum) şablonun dilinde yazdırılır.

## Ayarlar

**Ayarlar > Belge ayarları** (`Belge türlerini, şablonlarını ve ayarlarını yönetme`)

- **Seri numarası biçimi**: varsayılan `{TYPE}-{YYYY}-{SEQ:6}` → `ENR-2026-000001`. Belirteçler `{TYPE}` (tür kodu), `{YYYY}` ve `{YY}` (kurumun saat dilimine göre düzenlenme yılı) ve `{SEQ:n}` (n haneli bir sıra numarası) şeklindedir. Tam olarak bir `{SEQ:n}` zorunludur ve ondan sonra yalnızca düz metin gelebilir. Sıra her farklı önek için ayrı sayılır: `{TYPE}-{SEQ:6}` yıllar boyunca tür başına, `{YYYY}{SEQ:5}` türler boyunca yıl başına sayar. Eşzamanlı düzenlemeler hiçbir zaman çakışmaz (sayaç veritabanında atomik olarak artırılır).
- **Doğrulama geçerlilik süresi (gün)**: 0 her zaman demektir. Süre dolduktan sonra doğrulama sayfası "süresi doldu" yanıtını verir. Düzenlemenin kendisi kayıtta kalır.
- **Dile göre imzalayan**: mührün üstüne yazdırılan ad ("Rektör, Ninefruits Üniversitesi"), kurumun desteklediği her dil için bir alan. Şablondaki bir imzalayan önceliklidir.

## Düzenleme

Öğrenci kaydı ekranında **Belge düzenle**: tür (etkin olanlar), dil (kurumun dilleri), kullanım amacı, nüsha (1 ile 20 arası). **Belge düzenle** PDF'i oluşturup saklar ve öğrenci kaydına döner; bildirim, seri numarasını bir **PDF** bağlantısıyla gösterir.

Aşağıdaki durumlarda düzenleme reddedilir (ekran nedenini söyler):

- türün kimler için ayarı uymuyorsa (bir mezun için öğrenci belgesi, kayıtlı bir öğrenci için mezuniyet belgesi)
- tür etkin değilse
- o dil için şablon yoksa
- öğrenci için bir **belge engeli** yürürlükteyse (bir kısıtlama, [bölüm 20](20-registration.md)); önce kaldırın. Personel kısıtlamayı göremese bile engeller.
- öğrenci kaydı görüntüleme kapsamının dışındaysa veya personelin belge düzenleme yetkisi yoksa
- PDF hizmeti (Gotenberg) yanıt vermiyorsa: hiçbir şey düzenlenmez ve "PDF oluşturulamadı" gösterilir. Daha sonra yeniden düzenleyin.

Düzenleme işlem günlüğüne kaydedilir (`certificate.issued`: öğrenci numarası, tür, dil, seri numarası, nüsha; gerekçe olarak kullanım amacı).

## Düzenlenen belgeler

**Belgeler > Düzenlenen belgeler**: düzenlenme tarihi, seri numarası, tür ve dil, öğrenci numarası, ad, kullanım amacı, nüsha, durum, personel ve **PDF** ile **Doğrulama sayfası** bağlantıları (yeni sekme). Türe ve duruma göre süzün; seri numarası, öğrenci numarası veya ada göre arayın. Görüntüleme kapsamı öğrenci kayıtlarıyla aynıdır.

- **PDF**: saklanan dosyayı açar. Yeniden oluşturulmaz, bu nedenle tam olarak düzenlendiği hâliyledir.
- **Doğrulama sayfası**: herkese açık sayfayı açar.
- **Yeniden oluştur** (satır menüsü): mevcut verilerden yeni bir PDF oluşturur (örn. bir şablonu düzelttikten sonra) ve dosyayı değiştirir. Seri numarası ve doğrulama kodu korunur; sağlama toplamı değişir. Denetim olayı `certificate.rerendered`. `certificate_render` komutuyla aynıdır. İptal edilmiş belgeler yeniden oluşturulmaz.
- **İptal et** (satır menüsü): gerekçe zorunludur. Satır ve dosya korunur, durum iptal edildi olur ve doğrulama sayfası "iptal edildi" yanıtını verir. Denetim olayı `certificate.revoked`. İptal edilen bir belge geri alınmaz; yeni bir belge düzenlenir.

Kayıt satırları ekranda düzenlenemez veya silinemez (bir satır, sağlama toplamıyla birlikte salt okunur bir ayrıntı açar).

## Doğrulama

- Doğrulama URL'si (`{institution address}/verify/{code}/`) ve bir QR kodu belgenin altına yazdırılır. Kod rastgele 20 karakterlik bir dizedir (büyük harfler ve rakamlar); büyük/küçük harf fark etmez. Adres `APP_URL` ortam değişkeninden gelir.
- Sayfa oturum açmadan açılır ve adres (IP) başına dakikada 30 istekle sınırlıdır (aşıldığında HTTP 429). Arama motorlarından sayfayı dizinlememeleri istenir (`noindex`). Belgenin düzenlenip düzenlenmediğini, türünü, seri numarasını, düzenlenme tarihini ve maskelenmiş ad ile öğrenci numarasını gösterir. İptal edilmiş, süresi dolmuş ve bilinmeyen kodların her biri farklı bir yanıt alır. Sayfadaki kod alanı da bir kodu kontrol eder (`/verify/?code=...`).
- Teslim edilen bir PDF dosyasının kendisini kontrol etmek için kayıt ayrıntısındaki sağlama toplamını (SHA-256) dosyanın özetiyle karşılaştırın. `uv run manage.py certificate_verify {code}` komutu da bir kodu kontrol eder ([komutlar](../operations/commands.md)).
- Diğer sistemler aynı kontrolü aynı ayrıntılarla JSON olarak alır: `GET /api/v1/certificates/verify/<verification code>/` (oturum açmadan, adres başına dakikada 30 istek, [LMS entegrasyon kılavuzu](../../../lms-integration-guide.md)).

## Öğrenci portalı

**Belgeler** (öğrenci ve mezun menüsü): öğrencinin kendi kaydına düzenlenmiş belgeler (düzenlenme tarihi, tür ve dil, seri numarası, durum), PDF'leriyle. İptal edilenler durumlarıyla ancak PDF bağlantısı olmadan listelenir ve öğrenci iptal edilmiş bir belgenin PDF'ini indiremez (düzenleyen personel kaydı kontrol etmek için açabilir). Diğer öğrencilerin dosyaları açılamaz (uygulamada ve veritabanında zorunlu kılınır). PDF adresi `/certificates/{issue id}/download/` şeklindedir.

## Sık sorulan sorular

- **Ad yanlış yazılmış.** Kişinin ad varyantını (o dilde) düzeltin ve **Yeniden oluştur** işlemini yapın. Belge zaten teslim edilmişse iptal edin ve yenisini düzenleyin.
- **Şablonu değiştirdim; zaten düzenlenmiş belgeler ne olacak?** Değişmezler. Gerekirse **Yeniden oluştur** işlemini yapın (birçoğu için tek seferde `certificate_render` komutu).
- **Bir seri numarası atlandı.** Düzenleme sırasında bir hata oluştuğunda (örn. PDF hizmeti çalışmıyorsa) numara tüketilir ve hiçbir kayıt satırı kalmaz. Numaraların benzersiz olması garanti edilir, ardışık olması değil.
- **QR kodu `localhost` adresini gösteriyor.** Üretim sunucusunda `APP_URL` değerini kurumun adresine ayarlayın, ardından ilgili belgeler için **Yeniden oluştur** işlemini yapın.

## Bu kurulumun ekranları

Ekranlar ve işlevler özgün sistemdekilerle (Filament, Livewire) aynıdır; kullanım biçimleri biraz farklıdır.

- **Belge düzenle** bir iletişim kutusu yerine bir form sayfası açar. Özgün sistem düzenlemeden sonra PDF'i yeni bir sekmede açıyordu; burada öğrenci kaydı ekranına dönülür ve bildirimdeki **PDF** bağlantısı onu açar.
- Kayıtta **PDF** ve **Doğrulama sayfası** satırın sonundaki bağlantılardır; **Yeniden oluştur** (bir onay sayfası) ve **İptal et** (bir gerekçe sayfası) satır menüsündedir. Yeniden oluşturma yalnızca iptal edilmemiş belgelerde çalışır.
- Şablonlar tür düzenleme ekranının altında düzenlenir. Aynı dil için iki şablon reddedilir. Yalnızca `Temel verileri görüntüleme` yetkisiyle türler ve şablonlar salt okunurdur.
- Düzenleme sırasında PDF hizmeti başarısız olursa hiçbir şey düzenlenmez (özgün sistemde PDF'siz bir kayıt satırı kalabiliyordu).
- Düzenleme yetkisi yalnızca genel olarak verildiğinde geçerlidir (özgün sistem kapsamlı bir yetkiyi ekranda geçiriyor, ardından veritabanı satırı bir hatayla reddediyordu).
- Demoda (`setup_demo`), `certificate-officer@demo.test` kaydı, `student@demo.test` ise portaldaki **Belgeler** ekranını gösterir.

[Yönetici kılavuzu içindekiler](README.md)

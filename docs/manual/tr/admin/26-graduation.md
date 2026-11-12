# 26. Mezuniyet denetimi ve mezuniyet

Menü: **Mezuniyet > Mezuniyet denetimleri**, öğrenci kaydı görüntüleme ekranındaki **Mezuniyet denetimi** düğmesi, **Ayarlar > Mezuniyet ayarları** (diploma numarası biçimi, en düşük genel not ortalaması; `Mezuniyet işlemlerini yürütme` yetkisi). Öğrenciler kendi ilerlemelerini portalda **Mezuniyet koşulları** altında görür.

| Yetki | Neye izin verir |
|---|---|
| `Mezuniyet denetimlerini çalıştırma ve görüntüleme` | Denetimleri çalıştırma (tekli ve toplu) ve saklanan denetimleri görüntüleme |
| `Mezuniyet işlemlerini yürütme, koşul muafiyeti tanıma` | Mezuniyet işlemleri (toplu), koşul muafiyetleri |

Rol varsayılanları: Öğrenci İşleri her ikisine, Akademik İşler denetimlere sahiptir.

## Eski sistemden farklar

- **Koşullar kontrol edilir.** Eski sistemin (YUSTIC) mezuniyet denetim formu yalnızca ders türü başına kredileri ve not ortalamasını yazdırıyor ve bunları hiçbir şeyle karşılaştırmıyordu (denetim sonucu kutusu boştu). Yeni sistem müfredat yılı başına **mezuniyet koşullarıyla** ([bölüm 17](17-courses-and-curriculum.md)) karşılaştırır ve her koşulun karşılanıp karşılanmadığını raporlar.
- **Mezuniyetten önce denetim zorunludur.** Eski sistemde Z durum değişikliği kodunu girmek yeterliydi. Yeni sistem bir mezuniyeti yalnızca saklanan en son denetim karşılanmışsa işler.
- **Diploma numarasını sistem verir.** Eski sistem diploma numarası alanını kullanmıyordu ve diploma numarası elle yazılıyordu.
- Mezunlar başka bir tabloya taşınmaz. Yalnızca öğrenci durumu `Mezun` olarak değişir ve hesap mezun erişimini korur ([bölüm 13](13-status-changes-and-advisors.md)).

## Denetim kuralları

Öğrencinin **ana programı × müfredat yılı** için koşul seti bulunur ve her koşul kontrol edilir.

| Koşul türü | Kontrol |
|---|---|
| Bir ders türünde kredi | Ders türü o tür **veya onun altındaki bir tür** olan geçilmiş derslerin kredi toplamı ≥ en az kredi |
| Zorunlu dersler | Listedeki her ders geçilmiş. Ders kaydı sırasında geçerli olan **eşdeğer dersler** sayılır |
| Derslerden seçim | Listeden (eşdeğerler dahil) geçilen derslerin kredisi veya sayısı eşiğe eşit veya üzerinde |
| Geçilmiş sınav | O sınav türünde başarılı bir sonuç bulunması ([bölüm 24](24-assessments.md)) |

- "Geçilmiş", kesinleşmiş notu geçer not olan bir ders kaydı demektir (`is_passed`). Aynı kişinin diğer öğrenci kayıtlarında (yeniden kayıttan önce) geçilen dersler de sayılır.
- Koşul setinin **toplam kredisi** ve **Ayarlar > Mezuniyet ayarları** altındaki **en düşük genel not ortalaması** (varsayılan 2.0; boş: uygulanmaz) da kontrol edilir.
- Çift ana dallar ve yan dallar kendi koşul setlerine göre ayrı ayrı kontrol edilir ve birlikte gösterilir. Mezuniyet koşulu ana programın karşılanmış olmasıdır.
- Müfredat yılına uyan bir koşul seti olmadan denetim karşılanmış olmaz (setin oluşturulması gerekir).

## Denetimler

- **Hemen denetle**: öğrenci kaydı görüntüleme ekranındaki **Mezuniyet denetimi** düğmesi. Mevcut verileri hemen kontrol eder ve her koşul için geçilen ve eksik dersleri gösterir. **Bu denetimi kaydet** onu saklar.
- **Toplu denetimler**: **Mezuniyet denetimleri > Denetimleri çalıştır** (dönem, başlangıç sınıfı) veya `uv run manage.py degree_audit_run --term={term} --min-year-level=4 --actor=...` komutu ([işletim komutları](../operations/commands.md)). Kayıtlı her öğrenci için bir denetim saklanır.
- Saklanan bir denetim bir **anlık görüntüdür**. Sonraki not değişiklikleri onu değiştirmez; yeniden denetlemek yeni bir anlık görüntü ekler. Liste öğrenci ve program türü başına yalnızca **en son** denetimi gösterir ve mezuniyet işlemi de en son denetime bakar.

## Muafiyetler

Bölüm değişikliği, yatay geçiş veya değişim programı gibi bireysel durumlar için tek bir koşuldan muafiyet tanınır. İki kişi yer alır (2026-10-23 tarihli karar).

1. **Talep**: öğrenci kaydı görüntüleme ekranında **Koşuldan muaf tut** altında koşulu seçin ve gerekçeyi girin (`Mezuniyet işlemlerini yürütme, koşul muafiyeti tanıma` yetkisi). Denetim olayı `graduation.waiver_requested`.
2. **Onaylama veya reddetme**: **Mezuniyet > Koşul muafiyetleri** altında aynı yetkiye sahip **başka bir personel** onaylar (not isteğe bağlı) veya reddeder (not zorunlu). Hiç kimse kendi talebine karar veremez. Denetim olayları `graduation.waiver_approved`/`waiver_rejected`.
3. Denetimde yalnızca onaylanmış muafiyetler karşılanmış sayılır. Koşul başına bir bekleyen veya onaylanmış muafiyet olabilir.
4. **Kaldırma**: onaylanmış bir muafiyette **Muafiyeti kaldır** (gerekçe zorunlu) muafiyetin uygulanmasını durdurur ve geçmişi korur (durum `Kaldırıldı`, denetim olayı `graduation.waiver_lifted`). Zaten işlem görmüş bir öğrencinin mezuniyeti geri alınmaz.

Her adım veri değişikliği kaydında da görünür.

## Mezuniyet işlemleri

**Mezuniyet denetimleri** listesinde öğrencileri seçin ve **Mezun et** düğmesine tıklayın (mezuniyet tarihi, gerekçe). Her öğrenci için:

1. Öğrencinin kayıtlı olduğunu ve en son ana program denetiminin karşılanmış olduğunu kontrol eder. Aksi takdirde o öğrenci atlanır ve gerekçe raporlanır.
2. `Mezun` durum değişikliğini kaydeder (durum `Mezun`, mezuniyet tarihi). [Bölüm 13](13-status-changes-and-advisors.md)'ün durum değişikliği geçmişinde görünür.
3. Diploma numarasını verir. Biçim, **Ayarlar > Mezuniyet ayarları** altındaki `{PROGRAM}-{YYYY}-{SEQ:5}` biçimidir (varsayılan, örn. `CS-2026-00001`; belirteçler: `{PROGRAM}` program kodu, `{YYYY}`, `{YY}` mezuniyet yılı, `{SEQ:n}` önek başına sıra). Eşzamanlı işlemler hiçbir zaman çakışmaz.
4. Denetim olayı `graduation.processed` (öğrenci numarası, mezuniyet tarihi, diploma numarası, dayandığı denetim).

Mezunlar notlarını ve belgelerini portalda görmeye devam eder ve mezuniyet belgesi mezuniyet tarihini ve diploma numarasını yazdırır ([bölüm 23](23-certificates.md)). Hatalı bir mezuniyet bir durum değişikliğiyle (yeniden kayıt vb.) düzeltilir. Bir mezuniyeti geri alma işlevi yoktur.

## Sık sorulan sorular

- **Denetim "koşul seti yok" diyor.** Programın, öğrencinin müfredat yılını kapsayan bir mezuniyet koşulu seti yoktur. [Bölüm 17](17-courses-and-curriculum.md)'deki gibi bir tane oluşturun.
- **Bir eşdeğer ders tanınmıyor.** Eşdeğerliğin geçerlilik dönemi, dersin alındığı dönemin başlangıç tarihini içermelidir.
- **Diploma numarası biçimini değiştirirsem ne olur?** Bir sonraki düzenlemeden itibaren uygulanır. Önek değiştiğinde sıra yeniden 1'den başlar.

## Bu kurulumun ekranları

Ekranlar ve işlevler özgün sistemdekilerle (Filament, Livewire) aynıdır; bazı denetimler biraz farklı çalışır.

- **Mezuniyet > Mezuniyet denetimleri** listesi (`/admin/graduation/degreeaudit/`): süzgeçler varsayılan olarak program türü **Ana program** ve öğrenci durumu **Kayıtlı** şeklindedir. Bir satırdaki **Aç** saklanan denetimi gösterir; **Yeniden denetle** bir onay sayfası açar. **Denetimleri çalıştır**, listenin üstündeki işlem düğmesidir (dönem, başlangıç sınıfı, varsayılan 4).
- **Mezun et** için satırları işaretleyin, işlem listesinden **Mezun et** seçeneğini seçip çalıştırın: bir sayfa mezuniyet tarihini ve gerekçeyi sorar. İşlenemeyen öğrenciler öğrenci numaraları ve nedenleriyle uyarı olarak listelenir (en fazla 10).
- Öğrenci kaydındaki **Mezuniyet denetimi**, şu anda değerlendirilen denetimi kendi sayfasında gösterir; alttaki **Bu denetimi kaydet** onu saklar. **Koşuldan muaf tut**, koşulu seçmek ve gerekçeyi vermek için bir sayfa açar.
- **Mezuniyet > Koşul muafiyetleri** (`/admin/graduation/degreerequirementwaiver/`): durum süzgeci varsayılan olarak **Beklemede** şeklindedir ve menü bekleyenlerin sayısını gösterir. Bir satırdaki **Onayla**, **Reddet** ve **Muafiyeti kaldır** not (gerekçe) için bir sayfa açar. Bunları kendi talebiniz veya zaten karara bağlanmış bir muafiyet için açmak 403 döndürür.
- **Ayarlar > Mezuniyet ayarları** (`/admin/settings/graduation/`): diploma numarası biçimi yalnızca tam olarak bir `{SEQ:n}` ile kaydedilir. En düşük genel not ortalaması 0 ile 5 arasındadır; boş, uygulanmadığı anlamına gelir.
- Portaldaki **Mezuniyet koşulları** (`/portal/graduation/`): öğrencilerin ve mezunların menüsündedir. Birden fazla öğrenci kaydı olduğunda (yeniden kayıt) portalda seçilen kaydı kullanır.
- Mezuniyet işlemi, yetkileri (mezuniyet işlemi, kaydın kapsamı, durum değişikliği onay kapsamı) kontrol ettikten sonra durum değişikliğini ve diploma numarasını sistem bağlamında yazar; bu nedenle mezuniyet personelinin ayrıca `Öğrenci kaydı oluşturma ve düzenleme` yetkisine ihtiyacı yoktur. Veri değişikliği günlüğü yine de işlemi yapan kullanıcıyı belirtir.

[Yönetici kılavuzu içindekiler](README.md)

# 24. Sınavlar

Menü: **Sınavlar > Sınav oturumları**, **Sınav sonuçları**, **Sonuç düzeltmeleri**, **Sınav türleri**. Öğrenciler portalda **Sınavlar** altında kayıt olur ve sonuçlarını görür.

| Yetki | Neye izin verir |
|---|---|
| `Öğrenci kaydetme, sonuç girme ve yayımlama, dış sonuç kaydetme` | Öğrencileri kaydetme, kaydını iptal etme ve girmedi olarak işaretleme, sonuç girme, CSV içe aktarma, sonuçları yayımlama, düzeltme isteme, dış sonuçları kaydetme ve kaldırma, sonuç kaydını görüntüleme (öğrenci kaydı görüntüleme kapsamı içinde) |
| `Sınav türlerini, bölümlerini ve oturumlarını yönetme` | Türleri, bölümleri ve oturumları oluşturma ve düzenleme, bir oturumun geçme puanını değiştirme, düzeltme taleplerini onaylama ve reddetme |

Rol varsayılanları: Öğrenci İşleri ve Akademik İşler her ikisine sahiptir. Tür ve oturum ekranları ayrıca `Temel verileri görüntüleme` yetkisi gerektirir (rol varsayılanlarında vardır). Sonuçlar yalnızca öğrenci kaydı görüntüleme kapsamı içinde görünür; bu nedenle `Öğrenci kayıtlarını görüntüleme` (veya yönetme) yetkisini de verin.

## Eski sistemden farklar

- **Tür başına sabit sütun yok.** Eski sistemde (YUSTIC) `CET` içinde dil bilgisi, yazma, dinleme ve okuma olmak üzere dört sabit sütun, yeterlik sınavı için ders başına bir P/N harfi (`SSCORE_ADD`) ve bilgisayar sınavı için bir başka tablo (`COMEXAM`) vardı. Yeni sistem bölümleri ve puanlama yöntemini **sınav türü** üzerinde tanımlar ve her sınavı aynı oturum, kayıt ve sonuç yapısıyla ele alır.
- **Geçme kararı.** Eski sistemde dört bölümün toplamının baraj puanına eşit veya üzerinde olması, bölüm başına en düşük puan olmaksızın geçmek anlamına geliyordu. Yeni sistem türün (veya oturumun) geçme puanı ve **bölüm başına en düşük puanla** karar verir ve kararı sonuçta saklar. Başarılı/başarısız türlerde personel karar verir.
- **Kayıt aralığı ve kontenjan.** Eski sistemde yoktu. Bir oturumun kayıt için açılış ve kapanış zamanı ile kontenjanı vardır.
- **Sonuçları yayımlama.** Eski sistemde öğrenciler sonuçları girilir girilmez ve yalnızca en son oturum için görüyordu. Yeni sistemde öğrenciler sonuçları oturumun **Sonuçları yayımla** işleminden sonra görür ve her oturumun sonuçları saklanır. Sonucu olan bir oturum silinemez.
- **Dış sonuçlar.** Eski sistemde TOEFL veya TOPIK gibi dış sınavları kaydedecek bir yer yoktu (mezuniyet denetim formundaki HSK kutusu boş bir etiketti). Dış sonuçlar bir kanıt dosyasıyla kaydedilir.
- **Mezuniyet koşullarıyla bağlantı.** Eski sistemde bir kişi mezuniyet denetim formunu okuyup karar veriyordu. **Geçilmiş sınav** koşul türü bunu müfredata dahil eder ([bölüm 17](17-courses-and-curriculum.md)).

## Sınav türleri ve bölümler

**Sınav türleri**: kod, ad (dil başına), kategori (Dil, Yeterlik, Tez, Dış sınav), puanlama, en yüksek puan, geçme puanı, dış sonuçlar, etkin, sıra.

| Puanlama | Girdi | Karar |
|---|---|---|
| Puan | Bölüm başına puan (bölüm yoksa toplam) | Toplam ≥ geçme puanı ve her bölüm ≥ kendi en düşük puanı. Geçme puanı yoksa personel seçer |
| Başarılı/başarısız | Geçti veya geçmedi | Personel seçer |

**Bölümler** (tür düzenleme ekranının **Bölümler** sekmesi): kod (CSV sütun adı; harfler, rakamlar, `-`, `_`), ad, en yüksek puan, geçmek için en düşük puan (isteğe bağlı), sıra. Bölümler varsa toplam, bölüm puanlarının toplamıdır. Bölümün en düşük puanına eşit bir puan o bölümü geçer; bir puan bile altında kalmak, toplam ne olursa olsun öğrencinin geçememesi demektir.

Kore üniversite profilinin (`setup_install --profile=korean-university`) hazır olarak yüklediği türler:

| Kod | Tür | Karar | Not |
|---|---|---|---|
| `ENG_COMP` | İngilizce yeterlik sınavı | Puan, 60'ta geçer | Dinleme, okuma, yazma, dil bilgisi, her biri 25 puan |
| `COMP_EXAM` | Bilgisayar yeterlik sınavı | Başarılı/başarısız | |
| `THESIS` | Bitirme tezi | Başarılı/başarısız | |
| `TOPIK` | Korece Yeterlik Sınavı | Başarılı/başarısız, dış | Seviye ve sertifika numarası kaydedilir |

Profili yeniden çalıştırmak yöneticilerin değiştirdiği değerleri korur ve kaldırdıkları bölümleri geri getirmez.

## Oturumlar

**Sınav oturumları**: tür, tarih (tür başına benzersiz), yer, kontenjan, kayıt açılışı ve kapanışı, geçme puanı (boş: türün değeri). Oturum ekranının **Kayıtlılar** sekmesi kayıtları listeler.

- **Öğrenci kaydet** (öğrenci numarasını girin): personel, kayıt aralığından bağımsız olarak sınav tarihine kadar öğrenci kaydedebilir. Kontenjan uygulanır. Tarihi geçmiş bir oturuma kimse kaydedilemez. Sonuçlar yalnızca kayıtlı öğrenciler için girilir; kayıtlı olmayan öğrencilerin CSV satırları hata olarak raporlanır ve atlanır.
- Öğrenciler kayıt aralığı boyunca portalda kayıt olur ve kaydını iptal eder. Yalnızca kayıtlı ve kaydı dondurulmuş öğrenciler yapabilir. İptalden sonra yeniden kayıt olmak aynı kaydı yeniden etkinleştirir.
- **Sonuç gir**: bölüm başına puan (veya toplam), gerektiğinde geçti veya geçmedi, not. Yayımlamadan önce yeniden girmek sonucun üzerine yazar (denetim olayı `assessment.result_recorded`). **Yayımlandıktan sonra kilitlenir** (aşağıdaki düzeltme taleplerine bakın).
- **Girmedi**: kayıtlı ancak sınava girmemiş. Bir sonuç girilmesi kaydı yeniden kayıtlı durumuna getirir.
- **Kaydı iptal et**: sonucu olan bir kayıt iptal edilemez. Gerekçe isteğe bağlıdır.
- **Sonuçları yayımla**: bundan sonra öğrenciler bu oturumun sonuçlarını görür. Yayımlandıktan sonra sonuçlar doğrudan düzenlenemez veya silinemez; bir **düzeltme talebi** ile değişir (2026-10-23 tarihli karar). `assessment_publish_results` komutuyla aynıdır.
- Oturumun **geçme puanı** (türünkini geçersiz kılar): sınav zor olduğu için bir toplantıda baraj puanı düşürüldüğünde kullanılır. **Yayımlamadan önce** değiştirilebilir ve kaydedildiğinde o oturum için zaten girilmiş her sonuç saklanan puanlardan **yeniden değerlendirilir** (toplam yeni eşiğe göre, bölüm en düşük puanları türde ayarlandığı gibi). **Geçme puanını değiştirme gerekçesi** girildiğinde `assessment.pass_score_changed` denetim olayı eski ve yeni eşikleri, kararı değişen öğrenci numaralarıyla birlikte saklar. Kaydettikten sonra ekran kaç sonucun yeniden değerlendirildiğini gösterir. **Yayımlandıktan sonra** salt okunurdur (yalnızca düzeltme talepleri). Bölüm başına en düşük puan oturumda değiştirilemez (tür ayarı).
- **Sonuçları içe aktar (CSV)**: biçim aşağıdadır. Kayıtlı olmayan öğrencilerin satırları hata olarak atlanır. `assessment_import_results` komutuyla aynıdır.

CSV biçimi (başlık satırı, UTF-8, en fazla 5 MB):

| Sütun | İçerik |
|---|---|
| `student_number` | Öğrenci numarası (zorunlu) |
| Bölüm kodu (`LISTENING`, …) | Bölüm puanı. Büyük/küçük harf duyarsız |
| `total` | Bölümü olmayan türler için toplam |
| `passed` | `Y`/`N`. Başarılı/başarısız türler veya geçme puanı olmayan türler için zorunlu |
| `absent` | `Y` öğrenciyi girmedi olarak işaretler |
| `note` | Not |

Hatalı satırlar atlanır ve satır numaralarıyla sonuç mesajlarında (ekran, ilk 10 satır) veya çıktıda (komut) raporlanır. Hata metinleri, komut çıktısı gibi İngilizcedir.

## Sonuç düzeltmeleri

Yayımlanmış bir oturumun sonuçlarını değiştirme prosedürü. Not değişiklikleri gibi çalışır.

1. Oturumun **Kayıtlılar** sekmesinde **Düzeltme iste**: yeni puanlar (veya geçti ya da geçmedi) ve gerekçe. Sonuç başına bir bekleyen talep. Denetim olayı `assessment.correction_requested`.
2. **Sınavlar > Sonuç düzeltmeleri** altında `Sınav türlerini, bölümlerini ve oturumlarını yönetme` yetkisine sahip biri **Onayla** (not isteğe bağlı) veya **Reddet** (not zorunlu) düğmesine tıklar. **Hiç kimse kendi talebine karar veremez.**
3. Onaylandığında sonuç hemen yeni değerlere değişir (karar yeni puanlardan yeniden verilir) ve öğrenci bunu görür. Denetim olayları `assessment.correction_approved`, `assessment.result_corrected`. Talep eden kişi talep karara bağlanana kadar talebi iptal edebilir.

Liste varsayılan olarak bekleyen talepleri (tüm talepler için durum süzgecinde **Tümü**), mevcut değerler ve önerilen değerler yan yana olacak şekilde gösterir. Menü bekleyen taleplerin sayısını gösterir.

## Sonuç kaydı

**Sınav sonuçları**: her sonuç (oturumlar ve dış). Türe, kaynağa ve başarı durumuna göre süzün; öğrenci numarası veya ada göre arayın. Görüntüleme kapsamı öğrenci kayıtlarıyla aynıdır.

- **Dış sonuç kaydet** (listenin üstünde): öğrenci numarası, tür (yalnızca dış sonuçlara izin veren türler), sınav tarihi (gelecekte olamaz), toplam, seviye, geçti veya geçmedi, sertifika numarası, kanıt dosyası (PDF, JPG, PNG, 5 MB), not. Denetim olayı `assessment.external_recorded`.
- **Kanıt belgesi**: dosyayı açar. Öğrenciler kendi dosyalarını açabilir.
- **Kaldır** (satır): gerekçe zorunlu, denetim olayı `assessment.result_removed`. Yanlış girilmiş bir dış sonucu veya yayımlamadan önceki bir sonucu silip yeniden kaydetmek için. Kanıt dosyası da silinir. Yayımlanmış bir oturumun sonuçları kaldırılamaz (düzeltme talebi).

## Mezuniyet koşulları

**Müfredat ve şubeler > Mezuniyet koşulları** altında **Geçilmiş sınav** koşul türünü seçin ve **Sınav türü** alanını seçin. Öğrenci, o türde en az bir başarılı sonuçla (oturum veya dış) koşulu karşılar. Portaldaki **Sınavlar** sayfasının üst kısmı, öğrencinin müfredatının gerektirdiği türleri ve bunların geçilip geçilmediğini gösterir. Mezuniyet denetimi ([bölüm 26](26-graduation.md)) bu koşulu okur. Bir koşulun kullandığı tür silinemez (bunun yerine etkin olmaktan çıkarın).

## Öğrenci portalı

**Sınavlar**: müfredat koşulları ve bunların geçilip geçilmediği, kayda açık oturumlar (kayıt olma, iptal), kayıtlarım, sonuçlarım (yayımlanmış oturumlar ve dış sonuçlar, bölüm puanları, kanıt belgesi).

## Bu kurulumun ekranları

Ekranlar ve özellikler özgün sistemdekilerle (Filament, Livewire) aynıdır; kullanım biçimleri biraz farklıdır.

- **Sınav oturumları** listesinin satır menüsü: **Sonuçları yayımla** (onay sayfası), **Sonuçları içe aktar (CSV)** (dosya sayfası). Oturum ekranının üstündeki düğmeler: **Öğrenci kaydet** (sınav tarihine kadar), **Sonuçları içe aktar (CSV)**, **Sonuçları yayımla**. Süzgeçler: tür, sonuçlar yayımlandı.
- Oturum ekranının **Kayıtlılar** sekmesi bir duruma (Tümü, Kayıtlı, İptal edildi, Girmedi) tıklanarak süzülür. Satırdaki **Sonuç gir**, **Düzeltme iste**, **Girmedi** ve **Kaydı iptal et** bağlantıları bir giriş sayfası açar. Sonuç sayfasında türün her bölümü için bir puan alanı vardır ve puanlardan karar verilen türler için kural açıklanır.
- **Sınav sonuçları** listesinin üstünde **Dış sonuç kaydet**, satır menüsünde **Kaldır**. Kanıt sütunundaki bağlantı dosyayı yeni bir pencerede açar.
- **Sonuç düzeltmeleri** satır menüsü: **Onayla**, **Reddet**, **Talebi iptal et** (kendi talepleri).
- Kanıt adresi: `/assessment-results/{result ID}/evidence/` (yetki kontrolünden sonra indirilir). Portal adresi: `/portal/assessments/`.
- Komutlar: `uv run manage.py assessment_import_results {kind code} {date} {CSV} --actor=... [--dry-run]`, `uv run manage.py assessment_publish_results {kind code} {date} --actor=...` ([işletim komutları](../operations/commands.md)).

## Sık sorulan sorular

- **Bir öğrenciyi kayıt aralığı dışında kaydetmem gerekiyor.** Personel onları oturum ekranındaki **Öğrenci kaydet** ile kaydeder.
- **Geçme puanını yalnızca bu oturum için değiştirmek istiyorum.** Yayımlamadan önce oturumun geçme puanını bir gerekçeyle girip kaydedin. Zaten girilmiş sonuçlar hemen yeni eşiğe göre değerlendirilir.
- **Bir puanı yanlış girdim.** Yayımlamadan önce, üzerine yazmak için yeniden **Sonuç gir** işlemini yapın. Yayımlandıktan sonra bir **düzeltme talebi** oluşturun ve başka bir personelin onaylamasını sağlayın.
- **Sınava girmeyenlerle ilgili istatistikler.** **Kayıtlılar** sekmesini **Girmedi** durumuna göre süzün.

[Yönetici kılavuzu içindekiler](README.md)

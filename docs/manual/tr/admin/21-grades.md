# 21. Notlar

Menü: **Notlar > Not girişi durumu**, **Değerlendirme yöntemi talepleri**, **Not değişiklikleri**, **Dönem kayıtları**, **Ayarlar > Notlandırma politikası**. Öğretim elemanları portalda **Verdiğim dersler > Not gir** ekranını kullanır.

| Yetki | Neye izin verir |
|---|---|
| `Notları, not girişi durumunu ve dönem kayıtlarını görüntüleme` | Not girişi durumunu, dönem kayıtlarını ve öğrencilerin not dökümlerini görüntüleme |
| `Notları kesinleştirme ve iade etme, öğretim elemanları adına not girme, dönem kapatma` | Bir şubenin notlarını kesinleştirme veya iade etme, öğretim elemanları adına not girme (işlem aralığından bağımsız), not üst sınırları dışındaki notları istisna olarak gönderme, dönem kapatma, yeniden hesaplama. Bir birim kapsamıyla atandığında yalnızca o birimin açtığı şubeler |
| `Personel not üst sınırları dışında not gönderdiğinde bilgilendirilme` | İstisnai gönderim bildirimlerini alma. Bölüm başkanlarına ve öğrenci işleri başkanına bir birim kapsamıyla atanır |
| `Kesinleşmiş bir notun değiştirilmesini isteme` | Kişinin ders vermediği şubeler için değişiklik isteme (örn. akademik usulsüzlük nedeniyle bir notun iptali) |
| `Not değişikliklerini onaylama veya reddetme (kendi talepleri hariç)` | Not değişikliği taleplerini karara bağlama |
| `Not ortalaması, ders tekrarı, akademik durum ve onur derecesi politikasını yönetme` | Notlandırma politikası ayarları |

Öğretim elemanları kendi şubeleri için herhangi bir yetki olmadan not girer ve değişiklik ister. Rol varsayılanları: Öğrenci İşleri görüntüleme, kesinleştirme, onaylama ve istisna incelemesi yetkilerine; Akademik İşler görüntüleme, değişiklik isteme ve politika yetkilerine; Belge Sorumlusu ve Bölüm Sekreteri görüntüleme yetkisine sahiptir. Değerlendirme yöntemi talepleri `Şubeleri planlama` yetkisiyle karara bağlanır.

## Eski sistemden farklar

- Eski sistemde (YUSTIC) öğretim elemanının kaydettiği not hemen kesinleşiyordu ve öğrenci işleri notu doğrudan ekranda düzeltiyordu. Gerekçe ve onay adımı yoktu; bazı hesapların düzeltmeleri yedek kayıtlarda bile görünmüyordu. Yeni sistemde **gir → gönder → kesinleştir** aşamaları vardır ve kesinleşmiş bir not yalnızca **değişiklik talebini başka biri onayladığında** değişir. Bunu hem uygulama hem de veritabanı (tetikleyiciler) zorunlu kılar.
- Eski sistemde bir öğretim elemanı isteği manipüle ederek ders vermediği şubelere not kaydedebiliyordu. Yeni sistem atanmış öğretim elemanlarını ve yetki kapsamını sunucuda ve veritabanında kontrol eder.
- Not ortalaması, akademik uyarılar ve onur derecesi her ekranda anlık olarak hesaplanmaz; **dönem kayıtları** olarak saklanır. Dönem kapatıldığında o dönemin resmî kaydı hâline gelir.
- Ders tekrarı önceki notu genel not ortalamasından ancak **yeni not kesinleştikten sonra** çıkarır (eski sistem bunu ders kaydında çıkarıyor ve şube iptal edildiğinde geri almıyordu).
- Eski sistem yalnızca notlar menüsünü devre dışı bırakıyordu; notlar adres üzerinden görülebiliyordu. Yeni sistem not görüntüleme engellerini sunucuda uygular.

## Bir dönemin akışı

1. **İşlem aralıkları** ([bölüm 10](10-terms.md)): alt dönem başına bir **Not girişi** aralığı. Öğretim elemanları yalnızca bu aralıkta not girer ve gönderir.
2. Öğretim elemanları notları girer ve gönderir. `uv run manage.py grades_remind_missing {term}` notlarını göndermemiş öğretim elemanlarına hatırlatma e-postası gönderir.
3. **Not girişi durumu** ekranında her şubeyi kesinleştirin veya öğretim elemanına iade edin.
4. Tüm şubeler kesinleştiğinde **Dönem kayıtları > Dönemi kapat**. Dönem kayıtları, akademik durum ve onur derecesi belirlenir ve dönem **Notlar kapatıldı** durumuna geçer.
5. Bundan sonra değiştirilen notlar **Not değişiklikleri** üzerinden ilerler.

## Not ölçeği ve değerlendirme yöntemi

**Not ölçeği kurulumda sabitlenir ve değiştirilemez** (2026-10-23 tarihli karar), çünkü tüm notlar ve not ortalamaları bu ölçeğe dayanır. `uv run manage.py setup_install --grade-scale=4.5|4.3` ile ayarlayın; aksi takdirde ilk profilin ölçeği kullanılır (Kore üniversitesi 4.5, eski YUST 4.3). Temel veriler > Not ölçekleri altındaki **varsayılan** işareti taşınamaz ve varsayılan ölçek silinemez. Her notun **puan aralıkları** (alt ve üst %) ve not katsayıları bu ekranda düzenlenir ([bölüm 11](11-course-categories-and-grade-scales.md)).

Her şubenin bir **değerlendirme yöntemi** vardır. Varsayılan **Mutlak değerlendirme**dir.

| Değerlendirme yöntemi | Öğretim elemanının girdiği | Saklanan | Gönderme koşulu |
|---|---|---|---|
| Mutlak değerlendirme (varsayılan) | Öğrenci başına bir **puan (0–100)**. Not, puan aralığından çıkar ve seçilemez (yalnızca puanı olmayan notlar, örn. I, doğrudan seçilir) | Puan (özgün), not, not katsayısı | Her öğrenci için bir not |
| Bağıl değerlendirme | Öğrenci başına bir **not**. Puan girilmez (girilirse reddedilir) | Not, not katsayısı | Her öğrenci için bir not + **not üst sınırlarına** uyulması |
| Başarılı/başarısız ders | Değerlendirme yönteminden bağımsız olarak P/NP | Not | Her öğrenci için bir not |

- Bağıl değerlendirme isteyen bir öğretim elemanı not girişi ekranında **Bağıl değerlendirme iste** düğmesine (gerekçeyle) tıklar. Açan birim için `Şubeleri planlama` yetkisine sahip biri (bölüm sekreteri, akademik işler) bunu **Notlar > Değerlendirme yöntemi talepleri** altında onaylar veya reddeder (not zorunlu) ve öğretim elemanı e-postayla bilgilendirilir. Onaylandığında eski yöntemle girilmiş taslak notlar silinir. Notlar **gönderildikten** sonra ne talep ne değişiklik mümkündür. Personel yöntemi şube ekranında da değiştirebilir, ancak yalnızca notlar girilene kadar.
- Tekrar alınan derste en yüksek not: mutlak değerlendirmede üst sınırdan daha yüksek bir not verecek puan **üst sınır notuna indirilir** (puan korunur). Bağıl değerlendirmede üst sınırın üzerindeki bir not seçilemez.

## Not üst sınırları (bağıl değerlendirme)

**Ayarlar > Notlandırma politikası > Bağıl değerlendirme**: not grubu başına üst sınır (varsayılan A grubu %30, B grubu %40), üst sınırın üzerindeki tolerans (varsayılan 1 yüzde puanı), kontrol için en az notlandırılmış öğrenci sayısı (varsayılan 10).

- Not grupları harfe göredir: A+, A0 ve A- A grubunu; B+, B0 ve B- B grubunu oluşturur. Üst sınırı olmayan gruplar (C, D, F) sınırsızdır.
- Payda, şubede not ortalamasına giren bir notu olan öğrenci sayısıdır. Dersten çekilen öğrenciler ve P/NP/I hariç tutulur.
- En az öğrenci sayısının altındaki şubeler kontrol edilmez (7 öğrenciden %30 A sağlanamaz).
- Öğretim elemanları not girişi ekranında **Not üst sınırlarını kontrol et** ile mevcut dağılımı üst sınırlarla karşılaştırarak görür ve üst sınırların üzerinde **gönderemez**.
- Not yönetimi yetkisine sahip personel üst sınırların üzerinde gönderebilir, ancak bir **istisnai gönderim** olarak: gerekçe zorunludur, dağılım ve gerekçe işlem günlüğüne kaydedilir, `Personel not üst sınırları dışında not gönderdiğinde bilgilendirilme` yetkisine sahip olanlar (bir birim kapsamıyla atanmış bölüm başkanları, öğrenci işleri başkanı) bir e-posta alır ve şube **İstisna olarak gönderildi** olarak işaretlenir. **Not girişi durumu** yalnızca istisnai gönderimleri gösterecek şekilde filtrelenebilir.

## Not girişi (öğretim elemanları)

Portalda **Verdiğim dersler** altında şubenin **Not gir** ekranını açın. Ekranın üst kısmı şubenin değerlendirme yöntemini, giriş talimatlarını ve değerlendirme yöntemi talebini gösterir.

- Mutlak değerlendirme: puan girilir girilmez not görünür.
- Bağıl değerlendirme: yalnızca not seçilir. Puan sütunu yoktur. Üst sınırları **Not üst sınırlarını kontrol et** ile kontrol edin ve gönderin.
- Not listesi dersin notlandırma esasına göre belirlenir. Harf notlu derslerde harf notları, başarılı/başarısız derslerde P/NP gösterilir ([bölüm 11](11-course-categories-and-grade-scales.md)).
- **Taslağı kaydet** her zaman yapılabilir. Öğrenciler taslak notları görmez.
- **Notları gönder** her öğrenci için bir not gerektirir. Gönderildikten sonra öğretim elemanı notları artık değiştiremez. Yanlış bir not için kesinleştirmeden önce öğrenci işlerinden notların iade edilmesini isteyin veya kesinleştirmeden sonra değişiklik isteyin.
- Dersten çekilen öğrenciler W olarak gösterilir ve not almaz.

## Kesinleştirme ve iade (öğrenci işleri)

**Not girişi durumu**: bir dönemin şubeleri; gönderilmemiş, gönderilmiş ve kesinleşmiş not sayılarıyla. **Kesinleştirmeye hazır** filtresi yalnızca tüm öğrencilerin notlarının gönderildiği şubeleri gösterir.

- **Kesinleştir**: gönderilen notları kesinleştirir. Ders kayıtları **Tamamlandı** olur ve öğrenciler notlarını görür. Öğrencilerin dönem kayıtları yeniden hesaplanır. Birden fazla şube seçilip **Seçilenleri kesinleştir** ile kesinleştirilebilir. Notu henüz gönderilmemiş öğrencisi olan şubeler atlanır.
- **Öğretim elemanına iade et**: gönderimi gerekçeyle iptal eder. Notlar taslağa döner ve öğretim elemanı bir e-posta alır.
- **Notlar**: not girişi ekranını açar. Öğrenci işleri kesinleştirmeden önce işlem aralığından bağımsız olarak not girebilir veya değiştirebilir. Personel öğretim elemanının **gönderdiği** bir notu değiştirdiğinde eski ve yeni değerler `grades.submitted_changed` denetim olayına kaydedilir.

## Not değişiklikleri

Kesinleşmiş bir notu değiştirmenin tek yolu.

1. Talep: öğretim elemanı not girişi ekranında öğrenci için **Değişiklik iste** düğmesine tıklar (gerekçeyle; mutlak değerlendirmede yeni puan, bağıl değerlendirmede yeni not). Tekrar alınan dersteki üst sınır değişikliklere de uygulanır. Ders vermedikleri şubeler için `Kesinleşmiş bir notun değiştirilmesini isteme` yetkisine sahip personel aynı ekrandan talepte bulunur. Not başına yalnızca bir açık talep olabilir.
2. Karar: **Notlar > Not değişiklikleri** altında (varsayılan: bekleyenler listesi; menü bekleyen sayısını gösterir) **Onayla** veya **Reddet** düğmesine tıklayın (not zorunlu). Talep eden kişi kendi talebine karar veremez (bu bir veritabanı kısıtıyla da zorunlu kılınır).
3. Onaylandığında not (mutlak değerlendirmede puan ve not) hemen değişir ve öğrencinin dönem kaydı ile sonraki dönemlerin genel not ortalaması yeniden hesaplanır. Akademik durum ve onur derecesi, dönem kapatılırken belirlenen değerleri korur.

Talep eden kişi talep beklerken **Talebi iptal et** işlemini yapabilir. Her talep ve karar gerekçesiyle birlikte işlem günlüğüne kaydedilir.

## Not ortalaması hesaplama

| Öğe | Kural |
|---|---|
| Alınan kredi | Kesinleşmiş her ders (F, P, NP, I dahil) |
| Kazanılan kredi | Geçer notlar (F, NP, I hariç) |
| Ortalamaya giren kredi | Not ortalamasına dahil edilen notlar. F 0 katsayıyla sayılır; P/NP/I hariç tutulur |
| Not ortalaması | Toplam (not katsayısı × kredi) ÷ ortalamaya giren kredi. Yalnızca başarılı/başarısız derslerden oluşan bir dönemin not ortalaması yoktur |
| Ondalık basamak | Ondalık basamak sayısı ve yuvarlama (yarımı yukarı yuvarla, kes) politikadan gelir. Tam sayı aritmetiği kullanıldığından sınırlarda hata oluşmaz (örn. 3.4375 → 3.438) |
| Dönem not ortalaması | O dönemin tüm notları (ders tekrarıyla değiştirilen önceki bir not kendi döneminin not ortalamasında sayılmaya devam eder) |
| Genel not ortalaması | Tekrar alınan bir ders politikaya göre yalnızca bir kez sayılır: **Son deneme** (varsayılan; daha kötü olsa bile en son olan) veya **En iyi deneme**. Değiştirilen not genel kredilerin de dışında kalır ve not ekranında "genel not ortalamasında tekrar alınan dersle değiştirildi" olarak gösterilir |

Ders tekrarı ilişkisi ders kaydında kurulur ([bölüm 20](20-registration.md)): aynı dersi veya eşdeğer bir dersi yeniden almak, onu önceki ders kaydına bağlar.

## Akademik durum ve onur derecesi (dönem kapatma)

| Politika | Varsayılan | Eski YUST profili |
|---|---|---|
| Uyarı eşiği | Dönem not ortalaması 1.75'in altında | 1.3'ün altında |
| Yalnızca normal dönemleri değerlendir | Evet | Evet |
| İlişik kesme incelemesi için uyarı sayısı | 0 (kapalı) | 4 |
| Yalnızca art arda gelen uyarıları say | Hayır (toplam sayı) | Hayır |
| Onur derecesi için en düşük not ortalaması, ortalamaya giren en az kredi | 4.0, 15 kredi | 0, 0 (eski sistem yalnızca ilk N kişiyi alıyordu) |
| Başarısız ders varsa onur derecesi yok | Evet | Hayır |
| Not ortalaması ondalık basamağı | 2, yarımı yukarı yuvarla | 3, yarımı yukarı yuvarla |
| Not ölçeği (kurulumda sabitlenir) | 4.5 (KR45) | 4.3 (YUST43) |
| Not üst sınırları (bağıl değerlendirme) | A %30, B %40, tolerans 1 yüzde puanı, 10 öğrenciden itibaren kontrol | Aynı |

- **Akademik uyarı**: dönem not ortalamasının eşiğin **altında** olması. Yalnızca başarılı/başarısız derslerden oluşan bir dönem uyarı vermez.
- **İlişik kesme incelemesi**: uyarı sayısı eşiğe ulaştığında işaretlenir. İlişik kesmenin kendisi bir durum değişikliğidir ([bölüm 13](13-status-changes-and-advisors.md)).
- Yalnızca normal dönemler değerlendirildiğinde yaz ve kış dönemlerinin akademik durumu olmaz ve bunlar art arda gelen uyarı dizisini bozmaz.
- **Onur derecesi**: ölçütleri karşılayan öğrenciler program başına dönem not ortalamasına göre sıralanır (eşitler aynı sırayı paylaşır; sonraki sıra atlanır).
- Öğrenci kaydının **Akademik durum** alanı en son sonuca göre değişir. İşlem aralıklarının ve şube uygunluğunun "akademik durum" ölçütü bu değeri kullanır.

**Dönem kayıtları** ekranında akademik uyarıdaki öğrencilerin listesini ve onur listesini (eski uyarı ve onur raporları) görmek için döneme, akademik duruma, onur derecesine ve programa göre filtreleyin. **Dönemi kapat** işlemini önce **Yalnızca önizleme** seçeneğiyle (varsayılan) çalıştırarak kesinleşmemiş şubeleri görün, ardından bu seçeneği kapatıp yeniden çalıştırın. **Yeniden hesapla**, değiştirilen bir politikayı geçmiş dönemlerin kayıtlarına uygular (gerekçe zorunlu).

## Öğrenci ekranı ve not dökümü

Bir personel bir öğrencinin not dökümünü açtığında bu, `transcript.viewed` denetim olayına (öğrenci numarasıyla) kaydedilir.

- Portal **Notlar**: dönem başına kesinleşmiş notlar (dersten çekilmeler W olarak), dönem not ortalaması ve kazanılan kredi, genel not ortalaması, akademik durum, onur derecesi. Mezunlar da görebilir. Kesinleşmemiş notlar gösterilmez.
- **Yazdır**, **PDF**: kontrol amaçlı resmî olmayan bir not dökümü. PDF, Gotenberg tarafından oluşturulur. Resmî transkript belge olarak düzenlenir ([bölüm 23](23-certificates.md)). Personel bir öğrencinin not dökümünü öğrenci kaydı ekranında veya Dönem kayıtları'nda **Not dökümü** ile açar (`Notları, not girişi durumunu ve dönem kayıtlarını görüntüleme` yetkisi).
- Bir **kısıtlamada** **Not görüntülemeyi engeller** açık olan öğrenci not ekranını veya not dökümünü göremez ([bölüm 20](20-registration.md)).
- Ders değerlendirme aralığında, dönemin ders değerlendirmesini tamamlamamış bir öğrencinin o döneme ait notları gizlenir (bir ayar, [bölüm 22](22-course-evaluation.md)).

## Notlandırma politikası

**Ayarlar > Notlandırma politikası** (`Not ortalaması, ders tekrarı, akademik durum ve onur derecesi politikasını yönetme` yetkisi). Yukarıdaki tablonun öğelerini değiştirir. Değiştirilen politika bir sonraki hesaplamadan itibaren uygulanır. Geçmiş dönemlerin kayıtlarına uygulamak için **Yeniden hesapla**. Akademik durum ve onur derecesi dönem kapatılırken belirlendiğinden kapatılmış bir döneme yeniden uygulanmaz.

## Bu kurulumdaki ekranlar

Ekranlar ve işlevler özgün sistemdekilerle (Filament, Livewire) aynıdır; kullanım biçimleri biraz farklıdır.

- **Not girişi durumu** satır menüsü: **Notlar** (portaldaki not girişi ekranı), **Kesinleştir** (bir onay ekranı), **Öğretim elemanına iade et** (bir gerekçe ekranı). Birden fazla şubeyi kesinleştirmek için listede seçin ve işlem listesinden **Seçilenleri kesinleştir** seçeneğini seçin. Süzgeçler: dönem (varsayılan: devam eden dönem, tüm dönemler için **Tümü**), açan birim, istisna olarak gönderilen, kesinleştirmeye hazır.
- **Not değişiklikleri** ve **Değerlendirme yöntemi talepleri** satır menüsündeki **Onayla** ve **Reddet** not için bir ekran açar. Varsayılan liste bekleyen talepleri gösterir ve menü kaç talebin beklediğini gösterir.
- **Dönem kayıtları** listesinin üstündeki **Dönemi kapat**: dönem, **Yalnızca önizleme** (varsayılan olarak açık), gerekçe. Önizleme, dönemin kapatılıp kapatılamayacağını ve kesinleşmemiş şubeleri (en fazla 30) mesajlarla gösterir. Başlatılan bir kapatma, her biri 100 öğrencilik kuyruk görevleri (Celery) olarak çalışır; süren bir kapatma ilerlemesini dönem kayıtları listesinin üstünde gösterir. Bittiğinde dönem **Notlar kapatıldı** durumuna geçer ve kapatmayı başlatan personel bir e-posta alır. Bir görev başarısız olursa kapatma tamamlanmaz ve dönem olduğu gibi kalır; nedeni giderip yeniden kapatın (aynı sonucu verir). Komut satırından: `uv run manage.py term_close {term} --dry-run`, `uv run manage.py term_close {term} --reason=...` ([komutlar](../operations/commands.md)).
- **Notlandırma politikası** içinde not üst sınırlarını virgülle ayrılmış harf ve yüzdeler olarak yazın, örn. `A=30, B=40`. Boş, üst sınır olmadığı anlamına gelir.
- Portalda not girişi: mutlak değerlendirmede not, puan yazıldıktan kısa süre sonra puanın yanında görünür. **Taslağı kaydet**, **Not üst sınırlarını kontrol et** ve **Notları gönder** ekranın altındadır; kaydetme başarısız olduğunda (örn. aralık dışında bir puan) girilen değerler hatayla birlikte yeniden gösterilir. Bir öğrencinin satırındaki **Değişiklik iste**, talep alanlarını tablonun altında açar.
- Personelin not dökümü adresi: `/student-records/{student record id}/transcript/` (öğrenci kaydı ekranındaki **Not dökümü** düğmesi, bir dönem kaydı satırındaki **Not dökümü**). PDF için `?format=pdf` ekleyin.
- LMS'e bağlı bir şube için not girişi ekranı LMS puanlarını taslak olarak yükleyebilir ([bölüm 28](28-lms-integration.md)). Ders değerlendirmesi açık ve tamamlanmamış bir dönemin notları bir bildirim ve **Ders değerlendirme** bağlantısıyla gizlenir ([bölüm 22](22-course-evaluation.md)).

[Yönetici kılavuzu içindekiler](README.md)

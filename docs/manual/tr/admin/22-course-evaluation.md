# 22. Ders değerlendirme

Menü: **Ders değerlendirme > Dönem değerlendirmeleri**, **Değerlendirme formları**, **Şubelere göre yanıtlar**, **Ayarlar > Ders değerlendirme**. Öğrenciler portalda **Ders değerlendirme** ekranını, öğretim elemanları portalda **Verdiğim dersler > Ders değerlendirme sonuçları** ekranını kullanır.

| Yetki | Neye izin verir |
|---|---|
| `Ders değerlendirme yanıt oranlarını ve sonuçlarını görüntüleme` | Şube başına yanıt sayıları ve yanıt oranları, yayımlanmış sonuçlar. Bir birim kapsamıyla atandığında yalnızca o birimin açtığı şubeler |
| `Değerlendirme formlarını, dönem değerlendirmelerini ve yayımlamayı yönetme` | Formlar ve sorular, dönem değerlendirmesi ayarları, sonuçları yayımlama, ders değerlendirme ayarları |

Rol varsayılanları: Akademik İşler her ikisine, Bölüm Sekreteri görüntülemeye (bölüm kapsamı) sahiptir.

## Eski sistemden farklar

- **Anonimlik.** Eski sistem (YUSTIC) her yanıtla birlikte öğrenci numarasını saklıyordu ve öğretim elemanı hesapları ham tabloyu okuyabiliyordu. Yeni sistem **kimin değerlendirdiğini (tamamlama kayıtları)** ve **ne yanıtlandığını (yanıtlar)** ayrı ayrı saklar. Bir yanıt öğrenci, sıra numarası veya zaman bilgisi taşımaz. Yanıtlar veri değişikliği kaydına (denetim) da yazılmaz, çünkü denetim kaydı işlemi yapanı tutardı.
- **Sonuçları gösterme eşiği.** Eski sistemde öğretim elemanı ekranında en az yanıt eşiği yoktu ve öğretim elemanları diğer şubelerin sonuçlarını görebiliyordu. Yeni sistem sonuçları ve görüşleri, dönemin sonuçları **yayımlandıktan** sonra **yalnızca en az yanıt sayısına ve en düşük yanıt oranına ulaşmış şubeler için** gösterir. Öğretim elemanları yalnızca kendi şubelerini görür.
- **Not görüntüleme engeli.** Eski sistem yalnızca menü bağlantısını engelliyordu ve değerlendirme süresi bittiğinde kilit kaldırılmıyordu. Yeni sistem sunucuda engeller ve aralık kapandığında engeli kaldırır.
- **Soru yönetimi.** Eski sistem soruları her dönem SQL ile ekliyordu. Yeni sistem formları ve soruları ekranda yönetir.
- Tümü 1 veya tümü 5 olan yanıtları reddeden kural bir ayar hâline geldi (varsayılan olarak kapalı).

## Bir dönemi hazırlama

1. **Form**: **Değerlendirme formları** altında bir form seçin. Kore üniversite profili `STANDARD` formunu hazır olarak yükler (hazırlık, öğretim yöntemi, içerik, değerlendirme ve tesis ve donanım konularının her birinde 5 puanlık ölçekte 3 soru ve 1 görüş sorusu).
2. **Dönem hazırla**: dönem, form, en az yanıt sayısı, en düşük yanıt oranı (%). Varsayılanlar **Ayarlar > Ders değerlendirme** ayarından gelir (5 yanıt, %25). Sonuçların gösterilmesi için her iki eşiğin de karşılanması gerekir. Yanıt sayısı anonimliği korur (yalnızca birkaç yanıt olduğunda öğrenciler tahmin edilebilir); yanıt oranı sonuçların temsil edici olmasını sağlar.
3. **Değerlendirme aralığı**: dönem düzenleme ekranındaki **işlem aralıkları** arasına alt dönem başına bir **Ders değerlendirme** aralığı ekleyin ([bölüm 10](10-terms.md)). Hedef ölçütleri sınıf düzeyine göre aralıklar tanımlamaya olanak tanır.
4. Aralık süresince `uv run manage.py evaluation_remind {term}` değerlendirmeyi bitirmemiş öğrencilere hatırlatma e-postası gönderir (`--dry-run` yalnızca sayar). Yanıt oranlarını **Şubelere göre yanıtlar** altında görün.
5. Not işlemleri tamamlandığında **Sonuçları yayımla** (veya `uv run manage.py evaluation_publish_results {term}`). Komutlar [komutlar](../operations/commands.md) içinde açıklanmıştır.

## Formlar ve sorular

| Alan | Açıklama |
|---|---|
| Kod, Ad, Açıklama | Açıklama, öğrencinin değerlendirme ekranının üstünde gösterilir |
| Ölçek puanı sayısı | 2 ile 10 arası, genellikle 5 |
| 1 puanın etiketi, En yüksek puanın etiketi | örn. Kesinlikle katılmıyorum, Kesinlikle katılıyorum |

**Sorular** sekmesi: alan (aynı alandaki sorular gruplanır), soru, tür (Ölçek, Görüş), zorunlu, **Ters puanlı** (olumsuz ifade edilmiş bir soru; yanıt ortalamalarda ters çevrilir, örn. "Dersin temposuna ayak uydurmak zordu" sorusuna verilen 5, 1 olarak sayılır), sıra.

En az bir yanıtı olan bir formun soruları veya ölçeği artık değiştirilemez (böylece sonuçlar hiçbir zaman sorulmamış bir sorunun yanıtlarına dönüşmez). Değiştirmek için **Formu kopyala** ile yeni bir form oluşturun ve sonraki dönem onu kullanın.

## Neler değerlendirilir

- Dönem değerlendirmesi hazırlanmış bir dönemde kayıtlı veya tamamlanmış dersler. Dersten çekilinen ve bırakılan dersler hariç tutulur.
- **Ders değerlendirme** ayarı kapalı olan dersler hariç tutulur (uygulamalar, stajlar vb.; [bölüm 17](17-courses-and-curriculum.md)).
- Bir ders, yalnızca alt döneminin ders değerlendirme aralığı öğrenci için açıkken değerlendirilebilir.

## Öğrenci ekranı

Portal **Ders değerlendirme**: değerlendirilecek dersler listesinde **Değerlendir** düğmesine tıklayın, soruları yanıtlayın ve gönderin. Tüm zorunlu sorular yanıtlanmalıdır ve gönderim değiştirilemez. Her ders bir kez değerlendirilir.

**Not görüntüleme engeli** (bir ayar, varsayılan olarak açık): aralık süresince dönemde değerlendirilmemiş bir dersi olan öğrencinin o döneme ait notları portaldaki not ekranında ve not dökümünde bir bildirimle gizlenir. Değerlendirme tamamlandığında veya aralık sona erdiğinde notlar görünür. Diğer dönemlerin notları görünür kalır.

## Sonuçlar

- Öğretim elemanları: portalda **Verdiğim dersler** altında **Ders değerlendirme sonuçları**. Yalnızca dönemin sonuçları yayımlandıktan sonra açılır.
- Personel: **Ders değerlendirme > Şubelere göre yanıtlar** şube başına yanıt sayısını ve oranını gösterir; **Sonuçlar** sonuç ekranını açar. Ayrıntılı sonuçlar personele de yalnızca yayımlandıktan sonra gösterilir (aralık süresince sonuçlardaki değişiklikleri tamamlama zamanlarıyla eşleştirmek öğrencilerin kimliğini ortaya çıkarabilir).
- Sonuç ekranı: yanıtlar/beklenen (yanıt oranı), soru başına ortalama ve puan başına yanıt sayısı (ters puanlı sorularda ters çevrilmiş), genel ortalama, görüşler (rastgele sırayla).
- Yanıt sayısı en az yanıt sayısından az veya yanıt oranı en düşük oranın altında olan bir şube sonuçları ve görüşleri değil, yalnızca yanıt sayısını gösterir.

## Ayarlar

**Ayarlar > Ders değerlendirme**: değerlendirme tamamlanana kadar dönem notlarını gizle (varsayılan açık), tüm sorulara aynı yanıtı kabul etme (varsayılan kapalı), yeni bir dönemin değerlendirmesi için en az yanıt sayısı (varsayılan 5) ve en düşük yanıt oranı (varsayılan %25, eski öğrenci işleri ekranının eşiği).

## Bu kurulumdaki ekranlar

Ekranlar ve işlevler özgün sistemdekilerle (Filament, Livewire) aynıdır; kullanım biçimleri biraz farklıdır.

- **Dönem değerlendirmeleri** listesinin üstündeki **Dönem hazırla** bir giriş ekranı açar (dönem, form, en az yanıt sayısı, en düşük yanıt oranı). Boş bırakılan bir eşik, yeni bir dönem için ayardaki varsayılanı alır, mevcut bir dönem için geçerli değeri korur. Satır menüsündeki **Değiştir** aynı ekranı açar (dönem değiştirilemez); yanıtı olan bir dönemin formu değiştirilemez. Satır menüsündeki **Sonuçları yayımla** bir onay ekranı açar. Satır menüsü yayımlanmış dönemler için de gösterilir; bunlar için sonuçların zaten yayımlandığını belirten bir mesaj çıkar.
- **Değerlendirme formları** düzenleme ekranında sorular **Sorular** sekmesinde eklenir, değiştirilir ve silinir. Yanıtı olan bir form sorularını salt okunur gösterir ve ölçek puanları alanını kilitler. Üstteki **Formu kopyala** yeni kod için bir ekran açar; kopyalamadan sonra yeni formun düzenleme ekranı açılır.
- **Şubelere göre yanıtlar** süzgeçleri: dönem (varsayılan: ders değerlendirmesi olan en son dönem, tüm dönemler için **Tümü**), açan birim. Arama, ders kodunun başlangıcıyla eşleşir. Satır menüsündeki **Sonuçlar**, portaldaki sonuç ekranını (`/portal/sections/{section id}/evaluation/`) aynı pencerede açar.
- Portaldaki **Verdiğim dersler** tablosunun **Ders değerlendirme sonuçları** sütunu: dönemin sonuçları yayımlandığında bir **Sonuçlar** bağlantısı, aksi hâlde **Yayımlanmadı**.
- Öğrenci portalı **Ders değerlendirme**: **Gönder** tarayıcıda bir kez daha onay ister (JavaScript olmadan form doğrudan gönderilir). Zorunlu bir soru eksik olduğunda girilen yanıtlar hatayla birlikte yeniden gösterilir. Not ekranındaki bildirim **Ders değerlendirme** sayfasına bağlantı verir.
- Yanıtların saklanması: yanıt kimliği rastgele bir UUID'dir. Yanıtlar, cevaplar ve tamamlama kayıtları, öğrencinin ders kaydı, değerlendirme aralığı ve mükerrerlik kontrol edildikten sonra sistem bağlamında tek bir işlemde (transaction) yazılır ve veri değişikliği kaydına (denetim) yazılmaz. Bir formun kilitli olup olmadığı (yanıtı olup olmadığı), ekranı açan kişinin görüntüleme kapsamından bağımsız olarak değerlendirilir.

[Yönetici kılavuzu içindekiler](README.md)

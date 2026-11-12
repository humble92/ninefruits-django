# 12. Kişiler ve öğrenci kayıtları

Menü: **Öğrenciler ve personel > Kişiler**, **Öğrenci kayıtları**, **Öğretim elemanları**

## Kişiler ve öğrenci kayıtları arasındaki ilişki

| Kavram | Açıklama |
|---|---|
| Kişi | Tek bir insan. Ad, doğum tarihi, iletişim bilgileri, kimlik numaraları, fotoğraf, veliler. Öğrenci de olsa öğretim elemanı da olsa bir insan bir kişidir |
| Öğrenci kaydı | Tek bir giriş. Öğrenci numarası, program, giriş tarihi, sınıf, durum. Mezun olup yeniden kayıt yaptıran bir öğrenci aynı kişi üzerinde **yeni bir öğrenci kaydı (yeni öğrenci numarası)** alır |
| Öğretim elemanı | Kişinin öğretim elemanı bilgileri (sicil numarası, birim, kadro türü, akademik unvan). Kişi başına bir tane |
| Hesap | Oturum açma hesabı. Bir kişiye 1:1 bağlıdır. Birden fazla öğrenci kaydı olan bir kişinin yine tek bir hesabı vardır |

Öğrenciler ve mezunlar portalda bir öğrenci kaydı seçer (birden fazla kayıt olduğunda üst kısımda bir kayıt seçici görünür).

## Kişiler

- Bir kişinin hem **Latin harfleriyle ad** (pasaporttaki gibi resmî ad: soyadı, adı) hem de **Diğer dillerde ad** (örneğin Korece `김민수`) alanı vardır. Ekranlar, varsa geçerli dildeki adı, yoksa Latin harfleriyle adı gösterir. Arama her ikisini de bulur.
- Kimlik numaraları ve pasaport numaraları şifrelenmiş olarak saklanır ve maskelenmiş gösterilir. Kişi sayfasının üst kısmındaki **Kimlik numarasını göster** (veya **Pasaport numarasını göster**) düğmesine basıp bir gerekçe girdikten sonra tam değer ayrı bir sayfada bir kez gösterilir (`Kimlik ve pasaport numaralarını açık gösterme` yetkisi). Değer hiçbir yerde saklanmaz (ileti veya günlük yok) ve gösterim gerekçesiyle birlikte güvenlik günlüğüne yazılır. Numarayla arama yalnızca tam eşleşmeleri bulur.
- Fotoğraflar kişinin düzenleme sayfasında yüklenir. Bir fotoğraf yalnızca yetki denetiminden sonra indirilebilir (herkese açık bir adresi yoktur).
- Veliler kişinin ayrıntı sayfasındaki **Veliler** sekmesinde yönetilir. Öğrenciler de portaldaki **Bilgilerim** altında velilerini ve iletişim bilgilerini (e-posta, telefon, adres, posta kodu) düzenleyebilir. Adlarını, doğum tarihlerini veya kimlik numaralarını değiştiremezler.
- Kişi sayfasının altındaki **Değişiklik geçmişi**, kişinin ve velilerinin son 50 veri değişikliğini listeler (zaman, tablo, değişen sütunlar, kullanıcı). `Denetim kayıtlarını görüntüleme` yetkisiyle her değişikliği açabilirsiniz (önceki ve sonraki değerler). Öğrenci kaydı sayfası da kaydın, durum değişikliklerinin, danışmanların ve ikinci anadal ile yandalların geçmişini aynı şekilde gösterir.

| Yetki | İzin verdiği işlem |
|---|---|
| `Tüm kişileri görüntüleme` | Tüm kişileri görüntüleme |
| `Kişi oluşturma ve düzenleme` | Kişi oluşturma ve düzenleme |
| `Kimlik ve pasaport numaralarını açık gösterme` | Kimlik ve pasaport numaralarının tamamını görme |
| `Mükerrer kişileri birleştirme`, `Kişileri hesap oluşturmaya davet etme` | [Bölüm 14](14-merge-and-invitations.md) |

`Tüm kişileri görüntüleme` yetkisi olmayan personel de görmesine izin verilen öğrenci kayıtlarının arkasındaki kişileri ve öğretim elemanlarını görebilir.

## Öğrenci kaydetme

1. **Öğrenci kayıtları** listesinin üstündeki **Öğrenci kaydı ekle** düğmesine basın (sayfanın başlığı **Öğrenci kaydet**).
2. Bir **Mevcut kişi** seçin (yeniden kayıt, lisansüstü eğitime başlayan bir öğretim elemanı vb.) veya bir **Yeni kişi** girin. Yeni bir kişi oluşturmadan önce aynı kişinin zaten mevcut olup olmadığını aramayla kontrol edin.
3. Programı, giriş tarihini, sınıfı ve giriş türünü girin. Yönetici birim programdan alınır.
4. Öğrenci numarasının **Ayarlar > Öğrenci kayıtları** altındaki öğrenci numarası şablonuyla oluşturulması için alanı boş bırakın. Varsayılan şablon `{YYYY}{SEQ:5}`, giriş yılı ile 5 haneli bir sıra numarasından oluşur (örneğin `202600001`). Zaten kullanılan numaralar (içe aktarılan kayıtlar dahil) atlanır.

| Öğrenci numarası belirteci | Anlamı |
|---|---|
| `{YYYY}` | Giriş yılı |
| `{YY}` | Giriş yılının son iki hanesi |
| `{SEQ:n}` | n haneye tamamlanmış sıra numarası. Şablon tam olarak bir tane içermelidir. Her önek (örneğin `2026`) için ayrı sayılır |

Bir kaydın öğrenci numarası ve durumu düzenleme sayfasında değiştirilmez. Durum, durum değişiklikleriyle değişir ([bölüm 13](13-status-changes-and-advisors.md)).

## Öğrenci kayıtlarının görüntüleme kapsamı

| Yetki kapsamı | Görebileceğiniz öğrenci kayıtları |
|---|---|
| `Öğrenci kayıtlarını görüntüleme` veya `Öğrenci kaydı oluşturma ve düzenleme`, Tümü kapsamı | Tüm öğrenci kayıtları |
| Birim kapsamı | O birimdeki ve alt birimlerindeki kayıtlar (örneğin Mühendislik Fakültesi kapsamı = fakültenin tüm bölümleri) |
| Program kapsamı | O programdaki kayıtlar |
| Birim veya program kapsamı (çift ana dallar ve yan dallar) | O birimi veya programı çift ana dal ya da yan dal olarak izleyen öğrencilerin kayıtları (yalnızca görüntüleme) |
| Çift ana dal ve yan dal onaylayıcısı | Karar verilecek bir başvuru göndermiş öğrencilerin kayıtları (yalnızca görüntüleme) |
| Danışman | Mevcut danışmanlık öğrencileri |
| Öğrencinin kendisi | Kendi kayıtları |

Aynı kurallar veritabanında da (satır düzeyinde güvenlik) bulunduğundan, ekranların dışındaki sorgular (raporlar, doğrudan bağlantılar) da kapsamı aşamaz.

## Öğretim elemanları

**Öğretim elemanları** listesinin üstündeki **Öğretim elemanı ekle** ile (sayfanın başlığı **Yeni öğretim elemanı**) mevcut bir kişiyi seçin veya yeni bir kişi girin (`Öğretim elemanlarını yönetme` yetkisi). Bitiş tarihi geçtikten sonra öğretim elemanı, görevdeki öğretim elemanları listesinden (varsayılan filtre) ve danışman seçicisinden çıkar.

## CSV ile toplu yükleme

Öğrenci kaydı ve öğretim elemanı listelerinin üstündeki **CSV içe aktar** düğmesini kullanın. Sütun biçimleri [bölüm 9](09-csv-import.md#öğrenciler-ve-öğretim-elemanları) içindedir.

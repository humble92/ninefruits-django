# 2. Kullanıcılar ve roller

## Kavramlar

| Terim | Anlamı |
|---|---|
| Yetki | Bir özelliği kullanma hakkı. Örnekler: `Kullanıcıları görüntüleme`, `İki adımlı doğrulamayı sıfırlama` |
| Rol | Yetkilerden oluşan bir paket. Örnekler: öğrenci işleri, bölüm sekreteri |
| Rol ataması | Bir kullanıcıya kapsam ve süreyle birlikte bir rol verilmesi |
| Kapsam | Rolün geçerli olduğu alan: **Tümü**, **Birim** (fakülte, bölüm vb.) veya **Program** |
| Persona rolü | Aday, öğrenci, mezun, öğretim elemanı, danışman. Akademik verilerden otomatik olarak verilir; elle atanamaz |

Görev dağılımı değiştiğinde yalnızca rol yapılandırması veya atamalar değişir; programın kendisi değişmez. Her değişiklik denetim günlüğüne kaydedilir. Yönetim paneli menüsü ve her ekrandaki düğmeler yetkileri anında izler. Django'nun yerleşik "grupları" ve "süper kullanıcıları" kullanılmaz.

## Kullanıcı hesabı oluşturma

1. **Kullanıcılar ve erişim > Kullanıcılar** sayfasına gidip **Kullanıcı ekle** düğmesine basın.
2. Adı, e-posta adresini ve dili girip **Kaydet** düğmesine basın.
3. Kullanıcı, parola belirlemesi için e-postayla bir bağlantı alır. Yöneticiler parolayı hiçbir zaman görmez.

Hesaplar silinmez. Bir hesabı durdurmak için, örneğin biri kurumdan ayrıldığında, kullanıcıyı açın, **Etkin** seçeneğini kapatın ve kaydedin. Etkin olmayan bir hesapla oturum açılamaz ve hesap tüm yetkilerini kaybeder. Zaten oturum açılmış ekranlarda, bir sonraki istekte oturum kapatılır.

Hesap düzenlerken uygulanan güvenceler

- Kendi hesabınızı devre dışı bırakamazsınız.
- Sizin sahip olmadığınız yetkilere sahip bir hesabı (daha yüksek ayrıcalıklı bir yönetici) düzenleyemezsiniz.
- E-posta adresinin değiştirilmesi e-posta doğrulamasını sıfırlar, o kullanıcının tüm oturumlarını sonlandırır ve `E-posta değiştirildi` güvenlik olayını kaydeder.
- Bir kullanıcı parolasını değiştirdiğinde diğer cihazlardaki oturumlar ve hatırlanan cihazlar sona erer ve `Parola değiştirildi` güvenlik olayı kaydedilir.

## Rol oluşturma ve düzenleme

1. **Kullanıcılar ve erişim > Roller** sayfasına gidip **Rol ekle** düğmesine basın veya listeden bir rolü açın.
2. **Sistem adı** küçük harfler ve alt çizgilerden oluşur (örneğin `exam_office`). Oluşturulduktan sonra değiştirilmemesi en iyisidir.
3. **Görünen ad** alanını her dil için girin. İngilizce ad zorunludur. Bir dilin alanını temizlemek o dildeki adı kaldırır.
4. **Yetkiler** altında yetkileri özelliklere göre işaretleyin. Kaydettiğinizde eklenen ve kaldırılan yetkiler denetim günlüğüne yazılır.

| Rol türü | Düzenleme | Silme |
|---|---|---|
| Sistem rolü (sistem yöneticisi) | Yalnızca ad. Her zaman tüm yetkilere sahiptir | Mümkün değil |
| Persona rolü | Görünen ad ve yetkiler. Sistem adı değiştirilemez | Mümkün değil |
| Normal rol | Her şey | Yalnızca etkin ataması yoksa |

## Rol atama

1. **Kullanıcılar ve erişim > Kullanıcılar** sayfasına gidin ve kullanıcıyı açın. Alttaki **Rol atamaları** listesi mevcut ve geçmiş atamaları gösterir.
2. Sayfanın üst kısmındaki **Rol ata** düğmesine basın ve rolü, kapsamı, başlangıç/bitişi (isteğe bağlı) ve **Gerekçe** alanını girin.
   - Kapsam bir birim veya program ise **Kapsam hedefi** altında seçin. Bir birim seçildiğinde onun altındaki tüm birimler de dahil olur.
   - Hemen uygulanması için başlangıcı boş bırakın; süresiz bir atama için bitişi boş bırakın.
3. Atamalar hiçbir zaman düzenlenmez. Bir atamayı değiştirmek için mevcut atamada **Atamayı sonlandır** düğmesine basın (gerekçe zorunludur) ve yeni bir atama oluşturun. Geçmiş bozulmadan kalır.

Kendi atamalarınızı sonlandıramazsınız (görevler ayrılığı). Başka bir yöneticiden isteyin.

Ayrıcalık yükseltmeyi önleyen kurallar

- Kendinize rol atayamazsınız.
- Sahip olmadığınız yetkileri içeren bir rolü atayamazsınız.
- Kapsam yalnızca kendi `Rol atama ve sonlandırma` yetkinizin kapsamı içinde seçilebilir. Örneğin bu yetkiye Mühendislik Fakültesi için sahip olan bir yönetici, Tümü kapsamını veya başka bir fakültenin kapsamını atayamaz.
- İlk yöneticiyi oluşturan `security_create_administrator` komutu sunucu operatörü tarafından çalıştırıldığı için bu kurallar ona uygulanmaz ([komut başvurusu](../operations/commands.md)). Django'nun `createsuperuser` komutu kullanılamaz.

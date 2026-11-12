# 3. İki adımlı doğrulama

## Kullanıcıların kurulumu

Kullanıcılar kurulumu portalın **Güvenlik** sayfasında yapar (`/portal/security/`, yönetim panelinde kullanıcı menüsündeki **İki adımlı doğrulama**). Kurulumdan veya devre dışı bırakmadan önce parola bir kez daha doğrulanır.

### Kimlik doğrulama uygulaması (önerilir)

1. **İki adımlı doğrulamayı etkinleştir** düğmesine basın.
2. QR kodunu Google Authenticator veya Microsoft Authenticator gibi bir kimlik doğrulama uygulamasıyla okutun.
3. Uygulamada gösterilen 6 haneli kodu girip **Onayla** düğmesine basın.
4. Ekranda gösterilen **kurtarma kodlarını** güvenli bir yerde saklayın. Telefon kaybolursa her biri bir kez kullanılabilir.

### E-posta kodu

Yalnızca sistem yöneticisi izin verdiğinde gösterilir. Kimlik doğrulama uygulaması kullanamayan kullanıcılar içindir ve uygulamaya göre daha az güvenlidir.

1. **E-posta kodu** alanında **Kurulum için kod gönder** düğmesine basın.
2. Hesabın e-posta adresine gönderilen 6 haneli kodu girip **Onayla** düğmesine basın.
3. Bundan sonra her oturum açışta e-postayla bir kod gelir. Bir kod 10 dakika içinde bir kez kullanılabilir; 5 hatalı denemeden sonra yeni bir kod gerekir. Kodlar dakikada bir kez ve saatte en fazla 5 kez gönderilebilir.

İki yöntem birlikte kurulabilir. Politika "zorunlu" olduğunda kalan son yöntem devre dışı bırakılamaz.

## Politika ayarları (sistem yöneticisi)

Yönetim panelinde **Ayarlar > Güvenlik** altında ayarlanır. Kaydedilen ayarlar her kullanıcı için bir sonraki sayfa yüklemesinden itibaren geçerli olur.

| Ayar | Açıklama |
|---|---|
| Politika | **Kullanılmıyor** / **Önerilir (isteğe bağlı)**: kurulum yapmamış kullanıcılar yalnızca bir uyarı görür / **Seçilen roller için zorunlu**: seçilen rollere sahip kullanıcılar kurulum yapmak zorundadır / **Herkes için zorunlu** |
| İki adımlı doğrulama kullanması zorunlu roller | Politika "Seçilen roller için zorunlu" olduğunda seçilir |
| Geçiş süresi (gün) | Zorunluluk kullanıcıya ilk kez uygulandıktan sonra kullanıcının kurulum yapmadan çalışmaya devam edebileceği süre. Bu süre boyunca portalın ve yönetim panelinin üst kısmında son tarih uyarısı görünür. Süre dolduğunda yalnızca güvenlik sayfası kullanılabilir. 0, hemen anlamına gelir |
| Cihazları hatırlama süresi (gün) | **Bu cihazı hatırla** seçeneğinin işaretlendiği bir cihazda kodun istenmediği süre. 0 bu özelliği kapatır |
| E-posta kodlarına izin ver | Kapalıyken e-posta kodları iki adımlı doğrulama sayılmaz. Yalnızca e-posta kodu kurmuş kullanıcılardan politikaya göre bir kimlik doğrulama uygulaması kurmaları istenir |

Önerilen işletim: personel rolleri (öğrenci işleri, akademik işler, sistem yöneticisi vb.) için **Seçilen roller için zorunlu**, öğrenciler için önerilir.

## Sıfırlama (telefonun kaybolması vb.)

1. Kullanıcıyı **Kullanıcılar ve erişim > Kullanıcılar** altında açın.
2. Sayfanın üst kısmındaki **İki adımlı doğrulamayı sıfırla** düğmesine basın ve bir gerekçe girin (`İki adımlı doğrulamayı sıfırlama` yetkisi gerekir).
3. Kullanıcının kimlik doğrulama uygulaması, kurtarma kodları, e-posta kodu ve hatırlanan cihazları tümüyle temizlenir. Geçiş süresi yeniden başlar.

Kendi hesabınızı sıfırlayamazsınız. Sıfırlama, gerekçesiyle birlikte bir güvenlik olayı olarak ve işlem günlüğüne kaydedilir.

Tek yönetici telefonunu kaybeder ve yönetim paneline erişemezse, BT operatörü `uv run manage.py security_reset_mfa` ile sıfırlama yapar (Docker: `docker compose exec app uv run manage.py security_reset_mfa`, [komut başvurusu](../operations/commands.md)).

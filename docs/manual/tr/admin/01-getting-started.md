# 1. Başlarken

## Oturum açma

1. Tarayıcınızda `/accounts/login/` adresini açın. Oturum açmadan `/portal/` veya `/admin/` adresini açtığınızda da buraya gelirsiniz; oturum açtıktan sonra istediğiniz sayfaya dönersiniz.
2. E-posta adresinizi ve parolanızı girip **Oturum aç** düğmesine basın.
3. İki adımlı doğrulamayı kurduysanız kimlik doğrulama uygulamanızdaki 6 haneli kodu veya e-postayla aldığınız kodu girin.
4. Kişisel bir bilgisayarda **Bu cihazı hatırla** seçeneğini işaretleyebilirsiniz. Kod, ayarlanan süre boyunca (varsayılan 30 gün) istenmez. Ortak kullanılan bir bilgisayarda bu seçeneği işaretlemeyin.

Parolanızı unuttuysanız sıfırlama bağlantısı almak için oturum açma ekranındaki **Parolanızı mı unuttunuz?** bağlantısını kullanın. Art arda başarısız oturum açma denemeleri oturum açmayı geçici olarak engeller.

Yönetim panelinin kendine ait bir oturum açma ekranı yoktur. `/admin/login/` de sizi ortak oturum açma ekranına (`/accounts/login/`) yönlendirir.

## Portal ve yönetim paneli

| Ekran | Adres | Kullanıcılar |
|---|---|---|
| Portal | `/portal/` | Tüm kullanıcılar. Ana sayfa (erişim bilgileriniz), güvenlik ayarları ve kullanıcının personalarına (öğrenci, öğretim elemanı, danışman, aday) ait menüler |
| Yönetim paneli | `/admin/` | `Yönetim paneline erişme` yetkisine sahip personel |

İki ekran aynı oturum açma işlemini paylaşır.

- Üstteki portal menüsü yalnızca kullanıcının personalarına (öğrenci, öğretim elemanı, ...) ve yetkilerine uyan öğeleri gösterir. `Yönetim paneline erişme` yetkisi olanlar **Yönetim** öğesiyle yönetim paneline geçer.
- Yönetim panelinin sağ üst köşesindeki kullanıcı menüsü **İki adımlı doğrulama** (portal güvenlik ayarları) ve **Portal** bağlantılarını içerir ve oturumu kapatır (**Oturumu kapat**). İlk sayfa (**Pano**) hesap adını ve e-posta adresini, bir portal bağlantısını ve bir oturum kapatma düğmesini gösterir.
- Yetkisi olmayan bir hesapla yönetim paneli adresi açıldığında "403 Forbidden" gösterilir.

Yönetim panelinin solundaki menü yetkilerinize göre değişir. Menü, özgün grup sırasını korur (Öğrenciler ve personel, Öğrenci kabul, Müfredat ve şubeler, Ders kaydı, Notlar, Ders değerlendirme, Sınavlar, Belgeler, Mezuniyet, Raporlar, LMS entegrasyonu, Temel veriler, Kullanıcılar ve erişim, Denetim, Ayarlar); açabileceğiniz hiçbir ekranı olmayan gruplar gösterilmez. Bir menü görünmüyorsa sistem yöneticisinden rol ataması isteyin. Menünün üstündeki arama alanı menü öğelerini adlarına göre bulur.

## İki adımlı doğrulama bildirimi

İki adımlı doğrulama politikası "önerilen" olduğunda veya zorunlu bir politikanın geçiş süresi boyunca, portalın ve yönetim panelinin üst kısmında bir bildirim görünür. **Şimdi kur** portal güvenlik sayfasını açar. Bkz. [3. İki adımlı doğrulama](03-two-factor-authentication.md).

## Dil

Dili portalın üst kısmındaki dil seçiciyle (oturum açma ekranında da aynı seçici vardır) veya yönetim panelinin kullanıcı menüsündeki dil listesiyle değiştirin. Oturum açıkken değiştirdiğinizde seçiminiz hesabınıza kaydedilir ve bir sonraki oturum açışınızda da korunur. Hangi dillerin sunulacağına sistem yöneticisi **Ayarlar > Kurum** altında karar verir.

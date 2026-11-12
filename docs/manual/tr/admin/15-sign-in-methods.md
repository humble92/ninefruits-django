# 15. Oturum açma yöntemleri

Menü: **Ayarlar > Oturum açma yöntemleri** (`Oturum açma yöntemlerini ve SSO ayarlarını yönetme` yetkisi)

## Oturum açma adı

Varsayılan oturum açma adı hesabın e-posta adresidir. Öğrenci numarasıyla oturum açma etkinleştirildiğinde oturum açma ekranındaki alan "E-posta veya öğrenci numarası" olur.

| Öğrenci numarasıyla oturum açma | Davranış |
|---|---|
| İzin verilmez | Yalnızca e-posta |
| Yalnızca kayıtlı öğrenciler | Kayıtlı ve kaydı dondurulmuş öğrenci kayıtlarının öğrenci numaralarıyla oturum açılabilir |
| Kayıtlı öğrenciler ve mezunlar | Sona ermiş kayıtların (mezun, kendi isteğiyle ayrılmış vb.) öğrenci numaralarıyla da oturum açılabilir |

Birden fazla öğrenci kaydı olan bir kişi, hangi öğrenci numarasını kullanırsa kullansın aynı hesaba ulaşır.

## Hesap kilitleme

| Ayar | Açıklama |
|---|---|
| Başarısız deneme sonrası kilitleme | Art arda bu sayıda yanlış parola girildiğinde hesap kilitlenir. 0 kilitlemeyi kapatır |
| Kilit süresi (dakika) | Bu sürenin sonunda kilit otomatik olarak kalkar |

E-posta ve öğrenci numarasıyla yapılan denemeler aynı hesabın başarısız denemeleri olarak sayılır. Kilitli bir hesap, yanlış parolayla aynı mesajı alır; böylece hesabın var olup olmadığı açığa çıkmaz. Kilitlemeler güvenlik olayı olarak kaydedilir (**Oturum açma kilitlendi**).

Kilidi süresinden önce kaldırmak için **Kullanıcılar** ayrıntı sayfasındaki **Oturum açma kilidini kaldır** işlemini kullanın (gerekçe zorunlu, `Kullanıcıları düzenleme` yetkisi). Yönetim paneli kullanılamadığında BT operatörü `uv run manage.py security_unlock_user` komutunu kullanır.

## Kurumsal oturum açma (SSO)

Okulun OpenID Connect oturum açma hizmeti (örneğin Microsoft Entra ID, Google Workspace, Keycloak) kaydedildiğinde oturum açma ekranına "... ile oturum aç" düğmesi eklenir.

| Alan | Açıklama |
|---|---|
| Anahtar | Küçük harfli tanımlayıcı, örneğin `school`. Değiştirilirse mevcut bağlantılar bozulur |
| Düğme etiketi | Oturum açma ekranında gösterilen ad |
| Yayıncı (issuer) URL | Sağlayıcının issuer adresi. Bu adresin altında `/.well-known/openid-configuration` erişilebilir olmalıdır |
| İstemci kimliği, İstemci gizli anahtarı | Uygulamayı sağlayıcıya kaydederken alınan değerler. Gizli anahtar şifrelenmiş olarak saklanır |
| Kapsamlar (scopes) | Varsayılan `openid email profile` |
| İki adımlı doğrulama sayılır | Yalnızca kurumsal oturum açmanın kendisi iki adımlı doğrulama gerektiriyorsa açın. Açıkken bu oturum açma için burada ayrıca iki adımlı doğrulama istenmez |
| Sağlayıcıya kaydedilecek yönlendirme URI adresi | Ekranda gösterilen adresi (`https://<server>/auth/sso/<key>/callback/`) sağlayıcının uygulama ayarlarına aynen kaydedin |

### Hesap bağlama

| Mod | Davranış |
|---|---|
| Kullanıcılar kendi hesaplarını bağlar | Kullanıcı parolasıyla oturum açar ve portalda **Güvenlik > Kurumsal oturum açma** altında **Bağla** düğmesine basar (parola onayı gerekir) |
| Doğrulanmış kurumsal e-postaya göre otomatik bağla | Sağlayıcının doğruladığı e-posta bir öğrenci kaydındaki kurumsal e-postayla eşleştiğinde hesap ilk oturum açmada otomatik olarak bağlanır |

- Bağlanmamış bir kurumsal hesapla oturum açılmaya çalışıldığında, parolayla oturum açıp hesabı bağlamayı söyleyen bir bildirim gösterilir. Kurumsal hesap tek başına hiçbir zaman yeni hesap oluşturmaz.
- Bağlama ve bağlantıyı kaldırma işlemleri güvenlik günlüğüne kaydedilir.

### Parolayla oturum açmaya izin verme

**Kurumsal oturum açma kullananlara parola izni ver** kapatılırsa bağlı kullanıcılar yalnızca kurumsal oturum açmayı kullanabilir. Kurumsal hesaplar mezuniyetten sonra çoğu zaman silindiğinden bu ayarı açık bırakmanızı ve mezun olmak üzere olan öğrencilerden kişisel bir e-posta ve parola hazırlamalarını istemenizi öneririz. Mezunlar, hesabın oturum açma e-postası (kişisel e-posta) ve parolasıyla oturum açmaya devam eder.

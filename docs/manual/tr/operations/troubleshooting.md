# Sorun giderme

- Hedef kitle: BT operatörleri
- İlgili: [dağıtım kontrol listesi](deployment-checklist.md), [zamanlanmış işler](scheduled-jobs.md), [komut başvurusu](commands.md)

| Belirti | Kontrol edilecekler |
|---|---|
| Oturum açtıktan hemen sonra güvenlik sayfasına yönlendiriliyor | İki adımlı doğrulama politikası "zorunlu" ve geçiş süresi dolmuş. Kullanıcı kurulumu yaptığında çözülür. Politika **Ayarlar > Güvenlik** altındadır |
| Yönetim panelinde 403 | Kullanıcının `admin_panel.access` yetkisini (`Yönetim paneline erişme`) içeren geçerli bir rol ataması yok. Kullanıcıyı **Kullanıcılar ve erişim > Kullanıcılar** altında açın ve **Rol atamaları** listesini (süre, kapsam) kontrol edin |
| Bir menü öğesi eksik | Rolde o ekranın yetkisi yok (örneğin `roles.view`) |
| E-posta kodları ulaşmıyor | E-posta ayarları (`MAIL_*`, `DEFAULT_FROM_EMAIL`), **Denetim > Güvenlik olayları** altındaki `E-posta kodu gönderildi` kayıtları, gönderim sınırları (kullanıcı başına dakikada bir, saatte beş) |
| Oturum açma sayfası `429 Too Many Requests` yanıtı veriyor | Bir adres dakikada `LOGIN_RATE_LIMIT_PER_IP` (varsayılan 30) denemeyi aştı. Çok sayıda kullanıcı aynı anda engelleniyorsa `TRUSTED_PROXY_COUNT` değerinin gerçek proxy sayısıyla eşleştiğini kontrol edin (herkes Nginx adresiyle görünüyorsa); bir kampüs NAT'ının arkasında değeri artırın ([dağıtım kontrol listesi](deployment-checklist.md#proxyler-ve-istemci-adresi)) |
| Doğru parolayla oturum açma başarısız | Oturum açma kilitlenmiş (**güvenlik olayları** arasında `Oturum açma kilitlendi`) veya hesap etkin değil. Kilidi `uv run manage.py security_unlock_user <email> --reason="..."` ile kaldırın |
| Bir ekranda başkalarının verilerinden 0 satır görünüyor | Normal olabilir (satır düzeyi güvenlik). **Denetim > Veri değişiklikleri** içindeki kullanıcı sütununa bakarak DB oturumundaki işlemi yapan kişinin ayarlandığını doğrulayın |
| `400 Bad Request` | İstenen ana makine adı `DJANGO_ALLOWED_HOSTS` içinde değil |
| `403 CSRF verification failed` | `DJANGO_CSRF_TRUSTED_ORIGINS` içinde `https://` adresi eksik veya Nginx `X-Forwarded-Proto` başlığını iletmiyor |
| Sonsuz HTTPS yönlendirmeleri | Nginx `X-Forwarded-Proto $scheme` başlığını iletmiyor, bu nedenle Django isteği HTTP olarak görüyor (`SECURE_PROXY_SSL_HEADER`) |
| Stil veya betik içermeyen ekranlar, bir `manifest.json` hatası | `npm ci && npm run build` (`static/dist/`), `collectstatic`, Nginx `/static/` konumu. Üretimde `VITE_DEV_MODE=false` kullanılır |
| Ekranların bazı kısımları İngilizce görünüyor | `compilemessages --ignore=.venv` çalıştırılmamış (`.mo` dosyaları yok). Yeni metinler için `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | Uygulama `app_runtime` olarak DDL denedi. Migration'ları yalnızca `uv run manage.py migrate` veya `setup_install` ile çalıştırın (ikisi de otomatik olarak `app_migrator` kullanır) |
| `Audit records are append-only` | Bir denetim tablosunu güncelleme veya silme girişimi. Bu engelleme bilinçlidir |
| PDF üretimi başarısız | `uv run manage.py pdf_sample`, Gotenberg durumu, `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` |
| Kuyruk görevleri takılı kaldı | Flower içinde worker bağlantısını ve başarısız görevleri kontrol edin, `uv run celery -A config inspect active`, Redis bağlantısı (`REDIS_URL`) |
| Zamanlanmış işler çalışmıyor, `/api/v1/health/` `degraded` yanıtı veriyor | Beat durmuş (5 dakikadan uzun süredir zamanlayıcı sinyali yok). Beat sürecini ve günlüğünü kontrol edin. Yalnızca bir beat olmalı |
| Worker günlüğünde `Received unregistered task` | Worker hâlâ önceki kodu çalıştırıyor. Dağıtımdan sonra worker'ı yeniden başlatın |
| Bir dönem kapanışı tamamlanmıyor | Flower içinde başarısız `grading.close_term_records` görevleri. Nedeni giderin, ardından dönem kapanışını yeniden başlatın (öğrenci başına hesaplamalar yeniden çalıştırıldığında aynı sonucu verir) |

İstek bazında izleme: `X-Request-Id` yanıt başlığının değeriyle günlüklerde (JSON içinde `request_id`), işlem günlüğünde, veri değişikliklerinde ve güvenlik olaylarında birlikte arama yapabilirsiniz. Nginx `X-Request-Id $request_id` başlığını ilettiğinde Nginx erişim günlüğü de buna katılır. Komut çalıştırmaları `cmd-` ile başlayan bir çalıştırma kimliği kullanır.

# Yönetim komutu başvurusu

- Hedef kitle: BT operatörleri
- Kapsam: bu depodaki Ninefruits uygulamalarının kaydettiği tüm komutlar (`ninefruits/*/management/commands/`) ve işletimde kullanılan Django yerleşik komutları. Bir komut eklendiğinde bu belgeye de (16 dilin tümünde) bir `### \`command\`` girdisi eklenmelidir, aksi hâlde CI başarısız olur (`tests/tooling/test_command_documentation.py`).

## Ortak kurallar

Her komut `uv run manage.py {command}` olarak çalışır. Docker geliştirme ortamında `docker compose exec app uv run manage.py {command}`.

| Öğe | Kural |
|---|---|
| Ad | Özgün `{context}:{action}` adı `{context}_{action}` olur (Django komut adları `:` içeremez). Örnek: `term:close` → `term_close` |
| Denetim kaydı | Veri değiştiren komutlar (aşağıda "Denetim: kaydedilir"), her çalıştırmada komutu, argümanları, seçenekleri, işletim sistemi kullanıcısını, çıkış kodunu ve sonucu işlem günlüğüne (günlük `command`) yazar. Bunları yönetim panelinde **Denetim > İşlem günlüğü** altında kontrol edin |
| Çalıştırma kimliği | Her çalıştırma, istek kimliği yerine `cmd-` ile başlayan bir kimlik alır. İşlem günlüğü, o çalıştırmanın yaptığı veri değişiklikleri ve gönderdiği Celery görevleri aynı kimliği taşır; böylece "bu değişikliği hangi komut yaptı" sorusu kimlikle yanıtlanır. `--actor` operatörün verdiği bir değerdir, bu nedenle veri değişikliklerinin kullanıcı sütununa yazılmaz (gerçek işlemi yapan, işletim sistemi kullanıcısıdır) |
| `--actor=<email>` | Denetlenen tüm komutlarda ortaktır. Sorumlu yönetici hesabını kaydeder. Bilinmeyen bir e-posta çalıştırmayı durdurur |
| `--dry-run` | Hiçbir şeyi değiştirmeden sonucu yazdırır. Geri alınması zor işlemlerde bulunur |
| `--force` | Onay istemleri olmadan çalıştırır (zamanlamalar ve dağıtım betikleri için) |
| `--reason=` | Gerekçe gerektiren komutlarda bulunur |
| Çıkış kodları | 0 başarılı, 1 başarısız veya iptal edildi, 2 bir kontrol komutu sorun buldu |
| DB bağlamı | Komut çalışırken DB oturumundaki işlemi yapan kişi `system:command:{command}` olarak ayarlanır ve veri değişikliklerinde (tetikleyici) görünür |

## Django yerleşik komutları

### `migrate`

- Amaç: veritabanı migration'larını uygular. Django komutunun etrafındaki bir Ninefruits sarmalayıcısıdır: `--database` verilmezse şema sahibi bağlantısını (`migrator`, rol `app_migrator`) kullanır. Uygulama bağlantısının (`app_runtime`) DDL yetkisi yoktur. `showmigrations` ve `sqlmigrate` de varsayılan olarak `migrator` bağlantısını kullanır.
- Ne zaman: ilk kurulumda ve her dağıtımda (`setup_install` de bunu çalıştırır).
- Seçenekler: Django `migrate` ile aynı (`app_label`, `migration_name`, `--plan`, `--check`, `--database`).
- Denetim: kaydedilmez (şema değişiklikleri migration geçmişinde, `django_migrations` tablosunda tutulur)
- Örnekler

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- Başarısızlıkta: yetki hatalarında [kurulum kılavuzundaki](installation.md) veritabanı rolü hazırlığını (`db/sql/roles/`) kontrol edin.

### `collectstatic`

- Amaç: Vite derleme çıktısını (`static/dist/`) ve Django ile unfold statik dosyalarını `STATIC_ROOT` (`staticfiles/`) dizininde toplar. Web sunucusu (Nginx) bu dizini sunar.
- Ne zaman: her dağıtımda, `npm ci && npm run build` sonrasında.
- Seçenekler: `--noinput` (istem yok), `--clear` (toplamadan önce mevcut dosyaları sil).
- Denetim: kaydedilmez
- Örnekler

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- Amaç: çeviri dosyalarını (`.po`) çalışma zamanındaki `.mo` dosyalarına derler. `.mo` dosyaları depoda tutulmaz; bu nedenle her kurulumda ve dağıtımda çalıştırın. Sistemde `gettext` kurulu olmalıdır.
- Ne zaman: her dağıtımda ve çeviri dosyalarını düzenledikten sonra.
- Seçenekler: `--locale=` (örn. `ko`, `zh_Hans`, `lo`), `--ignore=.venv`.
- Denetim: kaydedilmez
- Örnekler

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- Amaç: **kullanılmaz.** Bir Django süper kullanıcısı rol ve yetki kataloğunu ve denetim izini atlar; bu nedenle bu komut bir hatayla (çıkış kodu 1) sona erer ve `security_create_administrator` komutunu gösterir.
- Bunun yerine: ilk yöneticiyi `security_create_administrator` ile oluşturun (sistem yöneticisi rol atamasını ve bir denetim kaydını içerir).
- Denetim: geçerli değil

## Kurulum ve demo (Aşama 1)

### `setup_install`

- Amaç: yeni kurulum ve güncelleme. Sırasıyla şunları çalıştırır: migration'lar, temel veriler (rol şablonları ve yetki eşitlemesi, ülkeler, diller, kod listesi türleri, birim türleri), kurum ayarları, not ölçeği, kurulum profilleri ve ilk yönetici. Yeniden çalıştırmak güvenlidir (mevcut veriler ve yöneticilerin değiştirdiği değerler korunur).
- Ne zaman: ilk kurulumda ve her dağıtımda.
- Seçenekler: `--institution-name=`, `--locale=` (varsayılan dil), `--timezone=` (örn. `Asia/Seoul`), `--profile=` (kurulum profili anahtarı, tekrarlanabilir: `korean-university`, `yust-legacy`), `--grade-scale=` (not ölçeği `4.5` veya `4.3`; bir kez ayarlandıktan sonra sabittir; boşsa ilk profilin ölçeği), `--admin-email=`, `--admin-name=`, `--force` (soru sormaz; yönetici parolası standart girdiden okunur).
- Denetim: kaydedilir (uygulanan profiller, yönetici oluşturulup oluşturulmadığı)
- Örnekler

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="Demo University" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="Administrator"
  ```

- Çıktıyı okuma: her adım için `DONE`. `Administrator exists`, bir Sistem Yöneticisi ataması bulunduğu için oluşturmanın atlandığı anlamına gelir.
- Başarısızlıkta: eksik anahtar hatası, `DJANGO_SECRET_KEY` ve `pii_generate_key` değerlerinin ortamda ayarlanması gerektiği anlamına gelir. Migration hatası: veritabanı rollerini kontrol edin ([kurulum](installation.md)). `The grade scale is fixed`, `--grade-scale` değerinin zaten sabitlenmiş ölçekten farklı olduğu anlamına gelir.

### `setup_demo`

- Amaç: hayalî bir üniversite oluşturur (birimler, programlar, binalar ve derslikler, bugünün çevresinde önceki, mevcut ve sonraki dönem ile işlem aralıkları, Kore üniversite profili). Rol başına sabit demo hesaplarını yazdırır (`registrar@demo.test` vb., parola `demo-password`). Büyük hacimler toplu eklemelerle oluşturulur.
- Ne zaman: geliştirme, eğitim ve tanıtım ortamları. **Üretimde (`DJANGO_ENV=production`) `--force` ile bile asla çalışmaz.**
- Seçenekler: `--size=tiny|small|medium|large` (yaklaşık 20/100/2.000/20.000 öğrenci; `tiny` testler ve hızlı kontroller için), `--seed=` (aynı değer, aynı veri), `--force` (onay yok).
- `--student-accounts`: kayıtlı her öğrenciye bir hesap verir ve yük testleri için özel depolamaya `load-accounts.csv` (e-posta, parola) yazar ([yük testi](load-testing.md)).
- Denetim: kaydedilir (boyut, tohum, süre)
- Örnek: `uv run manage.py setup_demo --size=small --seed=42 --force`
- Başarısızlıkta: temel veriler olmadan demo hesapları atlanır (rolleri eksiktir); önce `setup_install` çalıştırın. Aynı veritabanında yeniden çalıştırmak mevcut demo verilerini atlar.

## Temel veriler ve dönemler (Aşama 1)

### `reference_import`

- Amaç: temel verileri CSV'den, yönetim panelindeki **CSV içe aktar** ile aynı kurallarla içe aktarır (satırlar koda göre bulunup güncellenir, boş çeviri hücreleri mevcut değerleri korur, başarısız satırlar ayrı tutulur).
- Argümanlar: `type` `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`, `students` (öğrenci kayıtları), `instructors`, `courses` (ders sürümleri), `registration_holds` (kayıt kısıtlamaları) / `file` başlık satırı olan UTF-8 CSV.
- Seçenekler: `--actor=` (zorunlu; içe aktarma bu hesap altında kaydedilir ve sonucu o hesabın **CSV içe aktarmaları** ekranında görünür), `--chunk=100` (Celery görevi başına satır), `--dry-run` (yalnızca başlık kontrolü ve satır sayısı).
- Denetim: kaydedilir (tür, dosya adı, satırlar, içe aktarma numarası, başarısız satırlar)
- Sütun biçimi: [yönetici kılavuzu 9. bölüm](../admin/09-csv-import.md).
- Çıkış kodları: görevler hemen çalıştığında (eager worker'lar) sonuç yazdırılır ve başarısız satırlar 2 verir. İçe aktarma yalnızca kuyruğa alındığında 0. Sonuç ve başarısız satırlar CSV'si yönetim panelinde **Temel veriler > CSV içe aktarmaları** altındadır.
- Örnek: `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- Amaç: bir zaman noktasında devam eden dönemleri ve açık işlem aralıklarını (tür, dönem, alt dönem, ad, uygunluk, kapanış zamanı) gösterir. Dönem ve işlem aralığı ayarlarını kontrol etmek veya "ders kaydı neden açık değil?" gibi sorular için kullanılır.
- Seçenekler: `--at=` (varsayılan şimdi; örn. `"2027-02-15 09:00"`; saat dilimi verilmezse sunucu saat dilimi (UTC) uygulanır; `"2027-02-15 09:00 Asia/Seoul"` veya `2027-02-15T09:00+09:00` bir saat dilimi belirtir).
- Denetim: kaydedilmez (salt okunur)
- Çıktıyı okuma: tarihler kurum saat dilimine göre değerlendirilir. Planlanan veya arşivlenmiş dönemlerin işlem aralıkları hiçbir zaman açılmaz. Kapanış zamanları kurum saat diliminde gösterilir.

## Güvenlik (Aşama 0, 2)

### `security_create_administrator`

- Amaç: sistem yöneticisi rolüne sahip bir hesap oluşturur. Genellikle `setup_install` tarafından çağrılır.
- Seçenekler: `--email=`, `--name=`, `--password-stdin` (parola standart girdiden. Etkileşimsiz çalıştırmalar için zorunludur).
- Denetim: kaydedilir (oluşturulan kullanıcının kimliği)
- Örnek: `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator"`
- Örnek (etkileşimsiz): `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator" --password-stdin`
- Başarısızlıkta: `system_administrator role is missing`, önce `setup_install` çalıştırılması gerektiği anlamına gelir. Parola en az 12 karakter olmalıdır.

### `security_sync_permissions`

- Amaç: DB'deki yetki listesini koddaki yetki kataloğuyla hizalar. Yeni yetkiler oluşturulur; katalogda olmayan yetkiler silinir (ve tüm rollerden kaldırılır). Sistem rolleri her zaman tüm yetkileri alır.
- Ne zaman: dağıtımdan sonra (`setup_install` bunu temel veri adımının bir parçası olarak yapar).
- Seçenekler: `--dry-run` (yalnızca oluşturma/silme listesini yazdırır), `--force` (silme onayını atlar).
- Denetim: kaydedilir (oluşturulan/silinen yetkiler)
- Çıktıyı okuma: `create` ve `delete` satırları. Silme olduğunda bir onay istemi görünür.
- Başarısızlıkta: onaya "hayır" yanıtı vermek 1 koduyla çıkar ve hiçbir şeyi değiştirmez.

### `security_reencrypt_secrets`

- Amaç: bir `DJANGO_SECRET_KEY` yenilemesinden sonra, ondan türetilen bir anahtarla korunan sırları (kimlik doğrulama uygulaması TOTP sırları, kurtarma kodu tohumları, SSO istemci sırları) yeni anahtarla yeniden şifreler. O zamana kadar bunlar `DJANGO_SECRET_KEY_FALLBACKS` içindeki önceki anahtarla okunur. Önceki anahtarı kaldırmadan önce çalıştırın ([Anahtar yönetimi](security-keys.md)).
- Argümanlar/seçenekler: `--dry-run` (yalnızca hâlâ önceki bir anahtarla şifrelenmiş sırları sayar).
- Denetim: kaydedilir (sayılar)
- Çıktıyı okuma: `Dry run: 0 authenticator(s) and 0 SSO client secret(s) use a previous key.` önceki anahtarın kaldırılabileceği anlamına gelir. `cannot be decrypted`, bir değerin yapılandırılmış hiçbir anahtarla okunamadığı anlamına gelir: önceki anahtarı `DJANGO_SECRET_KEY_FALLBACKS` içine koyun ve yeniden çalıştırın.
- Örnek: `uv run manage.py security_reencrypt_secrets --dry-run`

### `security_reset_mfa`

- Amaç: bir kullanıcının iki adımlı doğrulamasını (kimlik doğrulama uygulaması, e-posta kodları, kurtarma kodları, hatırlanan cihazlar) sıfırlar. Kullanıcı bir sonraki oturum açmada yeniden kurulum yapar. Hiçbir yönetici yönetim paneline oturum açamadığında kullanın (örneğin tek yönetici telefonunu kaybettiğinde). Aksi hâlde yönetim panelindeki **Kullanıcılar > İki adımlı doğrulamayı sıfırla** işlemini kullanın.
- Argümanlar/seçenekler: `{user}` kullanıcı e-postası, `--reason=` (zorunlu), `--actor=` (zorunlu. Sıfırlamaya karar veren yönetici).
- Denetim: kaydedilir (hem işlem günlüğünde hem güvenlik günlüğünde, gerekçesiyle)
- Örnek: `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="Phone lost, identity verified by phone call" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- Amaç: art arda yanlış parola girilmesiyle kilitlenen bir hesabın kilidini kilit süresi bitmeden açar. Yönetim panelindeki **Kullanıcılar > Oturum açma kilidini kaldır** ile aynıdır.
- Argümanlar/seçenekler: `{user}` kullanıcı e-postası, `--reason=` (zorunlu).
- Denetim: kaydedilir (güvenlik günlüğünde de)
- Çıktıyı okuma: `The account is not locked.` hiçbir şeyin değiştirilmediği anlamına gelir.
- Not: kilit eşikleri (başarısız deneme, kilit süresi) yönetim panelinde **Ayarlar > Oturum açma yöntemleri** altında ayarlanır.

## Kişiler ve öğrenci kayıtları (Aşama 2)

### `people_find_duplicates`

- Amaç: aynı kişi gibi görünen kişileri listeler. Ölçütler aynı kimlik numarası (arama karması) veya aynı Latin harfli ad ve doğum tarihidir. Birleştirilmiş kişiler hariç tutulur.
- Seçenekler: `--limit=100` (yazdırılacak grup sayısı).
- Denetim: kaydedilmez (salt okunur)
- Çıkış kodları: mükerrer adaylar varsa 2.
- Sonraki adım: her grubu yönetim panelinde **Kişiler** altında inceleyin ve aynı kişiyse korunacak kişinin sayfasından **Mükerrer kaydı birleştir** işlemini çalıştırın. Birleştirme geri alınamaz ([Yönetici kılavuzu 14. bölüm](../admin/14-merge-and-invitations.md)).
- Örnek: `uv run manage.py people_find_duplicates --limit=50`

## Öğrenci kabul (Aşama 3)

### `admission_matriculate`

- Amaç: bir başvuru döneminin onaylanmış adayları için öğrenci kayıtları (yeni öğrenci numaraları) oluşturur. Yönetim panelinde **Öğrenci kabul > Başvurular** üzerindeki toplu **Öğrenci kaydı oluştur** ile aynıdır (`MatriculateApplicant`). Her aday ayrı işlenir; bu nedenle bir başarısızlık diğerlerini durdurmaz.
- Argümanlar/seçenekler: `cycle` başvuru dönemi kodu, `--term=` (zorunlu; giriş dönemi kodu, örn. `2027-SP`; giriş tarihi dönemin ilk günüdür), `--actor=` (zorunlu; `Kabul edilen adaylar için öğrenci kaydı oluşturma` yetkisine sahip bir hesap; yalnızca o hesabın kapsamındaki adaylar işlenir), `--dry-run` (yalnızca liste).
- Denetim: kaydedilir (başvuru dönemi, dönem, adaylar, oluşturulanlar, başarısız başvuru numaraları). Her aday ayrıca bir iş denetimi kaydı (`application.matriculated`) alır.
- Çıkış kodları: başvuru dönemi veya dönem kodu bilinmiyorsa ya da `--actor` eksikse 1, bir aday başarısız olduysa 2.
- Örnek: `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- Başarısızlıkta: `Only accepted offers without a student record ...` adayın zaten bir kaydı olduğu veya onaylamadığı anlamına gelir; `The program is not in effect on the admission date.` programın giriş tarihinde geçerli olmadığı anlamına gelir (programın geçerliliğini Temel veriler > Programlar altında kontrol edin); `not in your scope` başvurunun `--actor` hesabının kapsamı dışında olduğu anlamına gelir.

### `admission_expire_drafts`

- Amaç: kapanmış başvuru dönemlerinin taslak başvurularını ve ayarlanan süre boyunca değiştirilmemiş taslakları (**Ayarlar > Öğrenci kabul > Dokunulmamış taslakların süresi dolsun (gün)**, varsayılan 90) **Süresi doldu** olarak işaretler. Süresi dolan başvurular artık aynı döneme yeni bir başvuruyu engellemez.
- Ne zaman: her gün 03:10'da zamanlanmıştır (Celery beat görevi `admission.expire_drafts` bu komutu çalıştırır).
- Seçenekler: `--dry-run` (yalnızca sayım).
- Denetim: kaydedilir (süresi dolan sayısı)
- Örnek: `uv run manage.py admission_expire_drafts --dry-run`

## Şubeler (Aşama 4)

### `section_copy`

- Amaç: yeni bir dönemin planlamasını önceki bir dönemin şubelerinden başlatır. Yönetim panelindeki **Şubeler > Başka bir dönemden kopyala** ile aynıdır (`CopySections`). İptal edilmemiş şubeleri taslak olarak; öğretim elemanları (hâlâ görevdeyse), ders zamanları ve derslikler, kontenjan ayırmaları (serbest bırakma zamanları dönem başlangıç tarihleri arasındaki farkla kaydırılır) ve ders izlencesiyle (özel bir taslak olarak) birlikte kopyalar. Ders sürümü, yeni alt dönemin başlangıcında geçerli olan sürümle değiştirilir.
- Argümanlar/seçenekler: `from-term`, `to-term` dönem kodları (örneğin `2026-FA`), `--org-unit=` (yalnızca bu birim kodunun şubeleri; tekrarlanabilir), `--dry-run` (kopyalamayı bir işlem (transaction) içinde yapıp geri alır, bu nedenle rapor kesindir), `--actor=` (zorunlu. Yalnızca o hesabın `Şubeleri planlama` yetki kapsamındaki şubeler kopyalanır).
- Denetim: kaydedilir (kaynak ve hedef dönem, kopyalanan, atlanan ve gözden geçirilmesi gereken sayıları; gerçek bir kopyalama ayrıca `sections.copied` iş denetimi olayını kaydeder)
- Çıktıyı okuma: `skipped`, hedef dönemde aynı şube kodunun zaten bulunduğu veya geçerli bir ders sürümü olmadığı anlamına gelir; `note`, şubenin kopyalandığı ancak bir şeyin dışarıda bırakıldığı anlamına gelir (derslik zaten dolu olduğu için dersliksiz kopyalandı, emekli bir öğretim elemanı vb.). Alt dönemler koda göre eşleştirilir; yoksa şube tam dönem alt dönemine girer.
- Çıkış kodları: bilinmeyen bir dönem kodu veya eksik `--actor` için 1.
- Örnek: `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- Amaç: ders programını yayımlamadan önce bir dönemin şubelerini kontrol eder. Dersliklerin ve öğretim elemanlarının çift rezervasyonu DB tarafından zaten engellenir; bu komut DB'nin izin verdiği sorunları bulur: derslik kapasitesinin üzerinde kontenjan, alt dönem başlangıç tarihinde geçerli olmayan bir ders sürümü, emekli bir öğretim elemanı, kontenjanın üzerinde kontenjan ayırmaları, alt dönem dışındaki ders tarihleri. Ayrıca yedekten geri yükleme gibi kısıtlar olmadan gelen verilerdeki derslik çakışmalarını da kontrol eder.
- Argümanlar: `term` dönem kodu.
- Denetim: kaydedilmez (salt okunur)
- Çıkış kodları: sorun varsa 2, bilinmeyen bir dönem kodu için 1. Henüz öğretim elemanı, dersliği veya ders zamanı olmayan şubeler yalnızca bilgi için gösterilir (`Note`).
- Örnek: `uv run manage.py schedule_check_conflicts 2027-SP`

## Ders kaydı (Aşama 5)

### `registration_preflight`

- Amaç: ders kaydını açmadan önce bir dönemi kontrol eder. Ders kaydı ve ekle/bırak aralıklarını, kural setini, yayımlanmış şube sayısını, kontenjanı 0 olan şubeleri, kontenjanın üzerindeki kontenjan ayırmalarını, alt dönem başlangıç tarihinde geçerli olmayan ders sürümlerini, bir kredi sınırı kapsamına girmeyen etkin öğrenci sayısını ve kayıt kısıtlaması olan öğrenci sayısını gösterir.
- Argümanlar: `term` dönem kodu (örneğin `2027-SP`).
- Denetim: kaydedilmez (salt okunur)
- Çıkış kodları: sorun varsa 2. Eksik bir kural seti sorun olarak değil bilgi olarak gösterilir (kural varsayılanları uygulanır).
- Örnek: `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- Amaç: öğrenci şimdi (veya belirli bir zamanda) şubeye kayıt yaptırsaydı ne olacağını kural kural gösterir. Hiçbir şey kaydedilmez ve hiçbir deneme kaydedilmez. "Neden kayıt yaptıramıyorum?" soruları için kullanın.
- Argümanlar: `student-number` öğrenci numarası, `section` `ders kodu-şube kodu` (örneğin `CSE2010-01`).
- Seçenekler: `--term=` (dönem kodu. Varsayılan, o şubeye sahip en son dönemdir), `--at=` (değerlendirme zamanı. Örneğin `"2027-02-10 10:00 Asia/Seoul"`).
- Denetim: kaydedilmez (salt okunur)
- Çıktıyı okuma: kural başına geçti/kaldı, engelle/uyar ve mesaj. Bir istisnanın kapsadığı kural başarısız olarak gösterilir ancak engellemez. Kontenjan, kural tablosunun altında ayrıca gösterilir.
- Çıkış kodları: ders kaydı reddedilecekse 2.
- Örnek: `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- Amaç: boş kontenjanı olan şubeler için bekleme listesindeki öğrencileri sırayla kaydeder. Kayda almada her kural yeniden kontrol edilir; bir kuralı karşılamayan bekleme listesi kayıtları listeden çıkarılır (gerekçe kaydedilerek). Ders kaydı ve ekle/bırak aralıklarının ikisi de kapanmış şubelerin bekleme listelerinin süresi dolar. Öğrenciler sonucu e-postayla alır.
- Argümanlar/seçenekler: `term?` dönem kodu (varsayılan: bekleme listesi kaydı olan her dönem), `--actor=`.
- Denetim: kaydedilir (şubeler, kayda alınan, çıkarılan, süresi dolan sayıları)
- Ne zaman: bir bırakma, dersten çekilme veya kontenjan ayırmasının serbest bırakılmasında ilgili şube bir kuyruk işiyle hemen işlenir. Bu komut, kaçırılanları işleyen saatlik zamanlanmış güvenlik ağıdır.
- Örnek: `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- Amaç: serbest bırakma zamanı geçmiş kontenjan ayırmalarını (örneğin ana dal öğrencilerine ayrılan kontenjanlar) işlenmiş olarak işaretler ve o şubeler için bekleme listesinden kayda alma işini kuyruğa alır. Ayrılmış kontenjanlar, serbest bırakma zamanı geçer geçmez hesaplamada genel kontenjana dönüşür; bu nedenle bu komut yalnızca kontenjanları bekleme listesine devreder.
- Denetim: kaydedilmez (5 dakikada bir çalışır. Kayda alma sonuçları ders kaydı kayıtlarındadır)
- Ne zaman: zamanlanmış (5 dakikada bir, Celery beat görevi `registration.release_reserved_seats`). Kayda alma görevi şube başına `registration.promote_waitlist` görevidir (bir Redis kilidiyle şube başına aynı anda bir tane).
- Örnek: `uv run manage.py registration_release_reserved_seats`

## Notlar (Aşama 6)

### `term_close`

- Amaç: bir dönemi kapatır. Dönemdeki her not kesinleşmiş olmalıdır. Her öğrenci grubu (100) için dönem kaydını (krediler, dönem ve genel not ortalaması) hesaplar ve akademik durumu (iyi durum, akademik uyarı, ilişik kesme incelemesi) ve onur derecesi uygunluğunu belirler (bir Celery chord'unun `grading.close_term_records` görevleri); ardından bitirme görevi `grading.finish_term_close` onur derecelerini program başına sıralar, dönem kayıtlarını resmî kayıt olarak kapatır ve dönemi **Notlar kapatıldı** durumuna getirir. İlerleme `job_batches` içinde tutulur ve **Notlar > Dönem kayıtları** listesinin üstünde gösterilir. Bittiğinde başlatan personel bir e-posta alır. Yönetim panelindeki **Notlar > Dönem kayıtları > Dönemi kapat** ile aynıdır.
- Argümanlar/seçenekler: `term` dönem kodu, `--dry-run` (yalnızca dönemin kapatılıp kapatılamayacağını kontrol eder), `--reason=` (kayıtta tutulan gerekçe), `--actor=`.
- Denetim: kaydedilir (öğrenci sayısı, kesinleşmemiş notu olan şube sayısı, toplu iş kimliği). Kapatma bittiğinde `term.closed` denetim kaydı akademik uyarı, ilişik kesme incelemesi ve onur derecesi sayılarını tutar.
- Çıkış kodları: bazı şubelerde kesinleşmemiş notlar varsa 2 (şube başına kesinleşmemiş sayı yazdırılır). Dönem yayımlanmış durumda değilse 1.
- Ne zaman: not girişi ve kesinleştirme tamamlandıktan sonra. Toplu işi Flower'da ve dönem kayıtları ekranında izleyin. Bir Celery worker olmadan dönem durumu değişmez. Bir veritabanı hatasıyla başarısız olan bir grup 3 kereye kadar yeniden denenir; yine başarısız olursa toplu iş başarısız kalır ve dönem değişmez (nedeni giderip yeniden çalıştırın; yeniden çalıştırmak aynı sonucu verir).
- Örnekler: `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py term_close 2026-FA --reason="Fall 2026 grades closed" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- Amaç: dönem kayıtlarını (krediler, dönem ve genel not ortalaması) kesinleşmiş notlardan yeniden hesaplar. Değiştirilmiş bir notlandırma politikasını (not ortalaması ondalık basamakları, ders tekrarı işleme) geçmiş dönemlere uygulamak için kullanın. Akademik durum ve onur derecesi dönem kapanışında belirlenen değerleri korur. Onaylanmış bir not değişikliği o öğrenciyi otomatik olarak yeniden hesaplar; bu nedenle bunun için bu komut gerekmez.
- Seçenekler: `--term=` (o dönemde notu olan öğrenciler, o dönemden itibaren), `--student-number=` (tek bir öğrenci), `--reason=` (zorunlu), `--actor=`.
- Denetim: kaydedilir (öğrenci sayısı, gerekçe)
- Çıkış kodları: gerekçe yoksa veya bilinmeyen bir dönem kodu ya da öğrenci numarası için 1.
- Örnek: `uv run manage.py grades_recalculate --term=2026-SP --reason="GPA changed to three decimal places"`

### `grades_remind_missing`

- Amaç: notları henüz gönderilmemiş (girilmemiş veya taslak olarak kaydedilmiş) şubelerin öğretim elemanlarına e-posta gönderir. Şubeler öğretim elemanı başına tek bir iletide gruplanır.
- Argümanlar/seçenekler: `term` dönem kodu, `--dry-run` (göndermeden hedefleri yazdırır), `--actor=`.
- Denetim: kaydedilir (şubeler, öğretim elemanları, gönderilen iletiler)
- Ne zaman: not girişi aralığı kapanmadan birkaç gün önce. Gerekirse zamanlamaya ekleyin.
- Örnek: `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## Ders değerlendirme (Aşama 7)

### `evaluation_remind`

- Amaç: ders değerlendirme aralığı açıkken hâlâ değerlendirilmemiş dersleri olan öğrencilere e-posta gönderir. Kalan dersler öğrenci başına tek bir iletide (alıcının dilinde) gruplanır.
- Argümanlar/seçenekler: `term` dönem kodu, `--dry-run` (yalnızca hedef öğrenci sayısı, hiçbir şey gönderilmez), `--actor=`.
- Denetim: kaydedilir (hedef öğrenciler, gönderilen iletiler)
- Çıkış kodları: bilinmeyen bir dönem kodu için 1.
- Ne zaman: değerlendirme aralığı boyunca bir veya iki kez. Gerekirse zamanlamaya ekleyin.
- Örnek: `uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- Amaç: dönemin ders değerlendirme sonuçlarını öğretim elemanlarına yayımlar. Yönetim panelindeki **Ders değerlendirme > Dönem değerlendirmeleri > Sonuçları yayımla** ile aynıdır. Yayımlandıktan sonra bile sonuçlar yalnızca en az yanıt sayısına ve yanıt oranına ulaşan şubeler için görünür.
- Argümanlar/seçenekler: `term` dönem kodu, `--actor=` (`Değerlendirme formlarını, dönem değerlendirmelerini ve yayımlamayı yönetme` yetkisine sahip bir hesap; yayımlayan olarak kaydedilir).
- Denetim: kaydedilir (yanıt sayısı, zaten yayımlanmış olup olmadığı). İş denetimi `evaluation.published`.
- Çıkış kodları: bilinmeyen bir dönem kodu veya ders değerlendirmesi olmayan bir dönem için 1.
- Ne zaman: değerlendirme aralığı ve not işlemleri tamamlandıktan sonra. Zaten yayımlanmış bir dönem değiştirilmez.
- Örnek: `uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## Belgeler (Aşama 8)

### `certificate_verify`

- Amaç: bir belge doğrulama kodunu herkese açık doğrulama sayfasıyla aynı ölçütlerle kontrol eder. Türü, seri numarasını, düzenlenme tarihini ve maskelenmiş belge sahibini yazdırır.
- Argümanlar/seçenekler: `code` doğrulama kodu (büyük/küçük harf fark etmez).
- Denetim: yok (salt okunur)
- Çıkış kodları: geçerliyse 0; bilinmeyen bir kod, iptal edilmiş bir belge veya süresi dolmuş bir geçerlilik süresi için 2.
- Örnek: `uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- Amaç: düzenlenmiş bir belgenin PDF'ini mevcut veriler ve şablonla yeniden oluşturur ve saklanan dosyanın yerine koyar. Yönetim panelindeki **Belgeler > Düzenlenen belgeler > Yeniden oluştur** ile aynıdır. Seri numarası ve doğrulama kodu aynı kalır; sağlama toplamı değişir. PDF, Gotenberg tarafından oluşturulur.
- Argümanlar/seçenekler: `issue` seri numarası, `--reason=` (zorunlu), `--actor=` (`Belge düzenleme, yeniden oluşturma ve iptal etme` yetkisine sahip bir hesap).
- Denetim: kaydedilir (seri numarası, yeni sağlama toplamı); iş denetimi `certificate.rerendered`.
- Çıkış kodları: gerekçe yoksa, bilinmeyen bir seri numarası için veya PDF oluşturulamadığında 1.
- Ne zaman: bir şablonu, bir ad yazımını veya `APP_URL` değerini düzelttikten sonra belirli bir belgeyi yeniden üretmek için.
- Örnek: `uv run manage.py certificate_render ENR-2026-000001 --reason="Name spelling corrected"`

## Sınavlar (Aşama 9)

### `assessment_import_results`

- Amaç: bir sınav oturumunun sonuçlarını CSV'den girer. Yönetim panelindeki **Sınav oturumları > Sonuçları içe aktar (CSV)** ile aynı kurallar (yalnızca kayıtlı öğrenciler, geçme kararı puanlardan verilir, yayımlamadan önce yeniden girmek sonucun yerine geçer, yayımlandıktan sonra satırlar hata olarak raporlanır).
- Argümanlar/seçenekler: `type` sınav türü kodu / `held_date` sınav tarihi `YYYY-MM-DD` / `file` başlık satırı olan UTF-8 CSV, `--actor=` (zorunlu, sonuçları giren kişi olarak kaydedilir), `--dry-run` (yalnızca satır doğrulaması, hiçbir şey kaydedilmez).
- Sütun biçimi: [Yönetici kılavuzu 24. bölüm](../admin/24-assessments.md).
- Denetim: kaydedilir (oturum, dosya adı, satır sayısı, girilen/girmedi/hata sayıları). Her sonuç ayrıca `assessment.result_recorded` iş denetimi kaydını alır.
- Çıkış kodları: oturum bulunamadığında, dosya okunamadığında veya `--actor` eksik olduğunda 1; hatalı satırlar olduğunda 2 (diğer satırlar kaydedilir).
- Örnek: `uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- Amaç: bir oturumun sonuçlarını öğrencilere yayımlar. Yönetim panelindeki **Sınav oturumları > Sonuçları yayımla** ile aynıdır. Yayımlandıktan sonra sonuçlar yalnızca düzeltme talepleriyle değişir.
- Argümanlar/seçenekler: `type` sınav türü kodu / `held_date` sınav tarihi, `--actor=` (zorunlu, öğrenci kaydetme, sonuç girme ve yayımlama yetkisiyle).
- Denetim: kaydedilir (oturum, sonuç sayısı) ve `assessment.results_published` iş denetimi kaydı
- Çıkış kodları: oturum bulunamadığında, zaten yayımlanmışsa, `--actor` eksikse veya yetkisi yoksa 1.
- Ne zaman: sonuç girişi tamamlandıktan sonra.
- Örnek: `uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## Devam (Aşama 10)

### `attendance_generate_sessions`

- Amaç: bir dönemin her şubesi için ders zamanlarından (hafta günü, saat, ders saati) ders oturumları oluşturur. Öğretim elemanı portalındaki **Ders zamanlarından oluştur** ve yönetim panelinin **Ders oturumları** sekmesindeki **Oturumları oluştur** ile aynıdır. Mevcut oturumlar ve devam bilgileri korunur (yeniden çalıştırmak güvenlidir). İptal edilmiş şubeler atlanır.
- Argümanlar/seçenekler: `term` dönem kodu, `--section=` (ders kodu-şube kodu, örneğin `CSE2010-01`, yalnızca bir tane), `--dry-run` (yalnızca hedef şube sayısı), `--actor=`.
- Denetim: kaydedilir (dönem, şubeler, oluşturulan oturumlar)
- Ne zaman: dönem başlamadan önce, ders zamanları kesinleştikten sonra. Ders zamanları değiştiğinde yeniden çalıştırın.
- Örnek: `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## Mezuniyet (Aşama 11)

### `degree_audit_run`

- Amaç: kayıtlı her öğrenci için bir mezuniyet koşulu denetimi kaydeder. Yönetim panelindeki **Mezuniyet denetimleri > Denetimleri çalıştır** ile aynıdır. Kaydedilen en son denetim, mezuniyet işleminin temelidir. Her çalıştırma yeni anlık görüntüler ekler.
- Seçenekler: `--term=` (denetimin ait olduğu dönem kodu), `--student-number=` (tek bir öğrenci), `--min-year-level=` (yalnızca bu sınıf ve üstü), `--actor=`.
- Denetim: kaydedilir (öğrenci sayısı, koşulları karşılayan sayısı). `--actor` ile ayrıca `graduation.audits_run` iş denetimi kaydedilir.
- Çıkış kodları: bilinmeyen bir dönem kodu için 1.
- Ne zaman: mezuniyet incelemesinden önce (dönem sonu) ve koşul setlerini veya eşdeğer dersleri değiştirdikten sonra.
- Örnek: `uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## LMS entegrasyonu (Aşama 12)

### `lms_sync`

- Amaç: yayımlanmış şubeleri platforma gönderir (ders oluşturma ve bağlama, öğretim elemanları, kayıtlı öğrenciler). Yönetim panelinde **Ders bağlantıları > Yeniden eşitle** işleminin yaptığını bütün bir dönem için yapar. Zaten bağlı şubeler yalnızca yeniden güvenceye alınır (idempotent). Her adım **Eşitleme günlükleri** içinde tutulur.
- Argümanlar/seçenekler: `{platform}` platform kodu, `--term=` (dönem kodu, varsayılan bitmemiş her dönem), `--section=` (tek bir ders kodu-şube kodu, örneğin `CSE2010-01`), `--dry-run` (yalnızca gönderilecek olanı "skipped" olarak kaydeder), `--actor=`.
- Denetim: kaydedilir (platform, şubeler, üyeler, başarısızlıklar)
- Çıkış kodları: bilinmeyen bir platform veya dönem kodu için 1, herhangi bir şube başarısız olduğunda 2 (şube başına hata yazdırılır).
- Ne zaman: dönem başlamadan önce, yeni bir platform etkinleştirildikten sonra.
- Örnek: `uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- Amaç: platformdaki ders listelerini öğrenci bilgi sistemindeki ders kaydı listeleriyle karşılaştırır, eksik üyeleri ekler ve fazla olanları çıkarır. Henüz bağlı olmayan şubeler bütünüyle eşitlenir. Farklar eşitleme günlüğünde tutulur (`reconcile`, `payload` içinde `missing` ve `extra`).
- Argümanlar/seçenekler: `{platform?}` (verilmezse her etkin platform), `--term=` (varsayılan bitmemiş dönemler), `--dry-run` (yalnızca farkları kaydeder), `--actor=`.
- Denetim: kaydedilir (platform başına şubeler, eklenen/çıkarılan/başarısız sayıları)
- Çıkış kodları: bilinmeyen bir platform veya dönem kodu için ya da hiçbir platform etkin değilse 1, herhangi bir şube başarısız olduğunda 2.
- Ne zaman: her gün 02:30'da `lms.reconcile` görevi olarak zamanlanmıştır (Celery beat). Bir platform kesintisinden sonra elle çalıştırın.

### `api_issue_token`

- Amaç: bir hesap için bir API entegrasyon belirteci düzenler ([ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md)); genellikle yalnızca ihtiyaç duyduğu yetkilere sahip bir hizmet hesabı için (LMS: `lms.manage`, BI: `reports.view`). Belirteç standart çıktının ilk satırında **bir kez** yazdırılır; veritabanı yalnızca özetini tutar. İstekler onu `Authorization: Token <token>` başlığında gönderir.
- Argümanlar/seçenekler: `{email}` hesap e-postası, `--days=` (ömür 1 ile 365 gün arası, varsayılan `API_TOKEN_TTL_DAYS` = 90), `--reason=` (ne için olduğu, denetime kaydedilir), `--actor=`.
- Denetim: kaydedilir (`api.token_issued`: anahtar öneki ve sona erme; belirtecin kendisi asla)
- Çıkış kodları: bilinmeyen veya etkin olmayan bir hesap ya da aralık dışında bir ömür için 1.
- Örnek: `uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle callbacks" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- Amaç: bir hesabın API belirteçlerini (tümünü veya `--key=` ile birini) iptal eder. `--list` yalnızca belirteçleri listeler (anahtar öneki, düzenlenme ve sona erme zamanları).
- Argümanlar/seçenekler: `{email}`, `--key=` (anahtar öneki), `--list`, `--reason=`, `--actor=`.
- Denetim: kaydedilir (`api.token_revoked`: iptal edilen anahtar önekleri)
- Çıkış kodları: bilinmeyen bir hesap için veya `--key` ile eşleşen belirteç yoksa 1.
- Ne zaman: bir entegrasyon sona erdiğinde, bir belirteç sızmış olabileceğinde veya sorumlu kişi değiştiğinde.

## İşletim kontrolleri ve temizlik (Aşama 13)

### `system_health_check`

- Amaç: yapılandırmayı ve anahtarları (`DJANGO_SECRET_KEY`, PII anahtarları, `DEBUG`), DB bağlantısını ve rollerini (runtime, migrator, reporting), kişisel veri tablolarındaki RLS'yi, bekleyen migration'ları, yetki kataloğu eşitlemesini, Redis'i, Celery worker'larını, Gotenberg'i, özel depolamaya yazmayı ve beat sinyalini (`core.heartbeat`, 5 dakika içinde) kontrol eder.
- Seçenekler: `--json` (izleme için çıktı).
- Denetim: yok (salt okunur)
- Çıkış kodları: herhangi bir kontrol başarısız olursa 2.
- Ne zaman: dağıtımdan hemen sonra, bir kesintiden şüphelenildiğinde, izlemeden düzenli olarak. Yük dengeleyiciler `/api/v1/health/` kullanır.
- Örnek

  ```bash
  uv run manage.py system_health_check
  uv run manage.py system_health_check --json
  ```

### `audit_seal`

- Amaç: denetim tablolarının (`audit.record_changes`, `audit.activity_log`, `audit.security_events`) yeni satırlarını karma zincirine bağlar ([Denetim bütünlüğü](audit-and-maintenance.md)). Şema sahibi bağlantısında (`migrator`) çalışır.
- Seçenekler: `--table=` (record_changes, activity_log, security_events'ten biri; tekrarlanabilir), `--actor=`.
- Denetim: kaydedilir (tablo başına mühürlenen satırlar)
- Ne zaman: her gün 03:30'da zamanlanmıştır.
- Örnek

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- Amaç: kurcalamayı, silmeleri ve yeniden sıralamayı bulmak için denetim satırlarının içerik karmalarını ve zincirini yeniden hesaplar. Tablo başına kontrol edilen satırları, mühürlenen satırları, uyuşmazlıkları ve ilk uyuşmayan kimliği yazdırır.
- Seçenekler: `--table=`.
- Denetim: yok (salt okunur)
- Çıkış kodları: bir uyuşmazlık varsa 2.
- Ne zaman: yedeklemelerden önce, güvenlik incelemeleri sırasında, temizlemeden sonra.

### `audit_prune`

- Amaç: saklama süresi geçmiş **mühürlenmiş** denetim satırlarını siler. Şema sahibi bağlantısında, `app.audit_maintenance = on` ile bir işlem (transaction) içinde çalışır. Mühürlenmemiş satırlar korunur (önce `audit_seal` çalıştırın). Her silme `audit.pruned` güvenlik olayını kaydeder (tablo, kesim tarihi, silinen satırlar, kimlik aralığı, sınır satırının `chain_hash` değeri).
- Seçenekler: `--before=YYYY-MM-DD` (zorunlu; o günün gece yarısından önceki satırlar), `--table=`, `--dry-run` (yalnızca sayılar), `--actor=`.
- Denetim: kaydedilir (kesim tarihi, tablo başına silinen satırlar ve kimlik aralığı)
- Ne zaman: saklama politikasına göre, bir yedeklemeden sonra.
- Örnek

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu
  ```

### `media_prune_orphans`

- Amaç: sahibi artık bulunmayan medya satırlarını ve özel depolamada satırı olmayan dizinleri (`<media id>/`) siler (kişi fotoğrafları, başvuru evrakları, belge PDF'leri, sınav kanıtları).
- Seçenekler: `--dry-run` (yalnızca liste), `--actor=`.
- Denetim: kaydedilir (satırlar, dizinler)
- Ne zaman: ayda bir veya toplu bir silme işleminden sonra.

## Kişisel veri şifreleme anahtarları (Aşama 0)

### `pii_generate_key`

- Amaç: `PII_ENCRYPTION_KEY` ve `PII_HASH_KEY` için yeni anahtarlar (32 bayt, `base64:...`) yazdırır. Hiçbir şey kaydetmez.
- Denetim: kaydedilmez
- Dikkat: `PII_HASH_KEY` değerini değiştirmek tüm arama karmalarını (`*_hash`) geçersiz kılar. Yalnızca şifreleme anahtarını yenileyin: eski anahtarı `PII_PREVIOUS_KEYS` içine taşıyın, ardından `pii_reencrypt` çalıştırın.
- Örnek

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- Amaç: bir anahtar yenilemesinden sonra, önceki bir anahtarla şifrelenmiş kişisel verileri geçerli anahtarla yeniden şifreler. Kayıt grupları üzerinde bir Celery görev grubu olarak çalışır. Zaten geçerli anahtardaki kayıtlara dokunulmaz.
- Argümanlar: şifrelenmiş kişisel veri alanları olan model (`app_label.Model`, örn. `person.Person`).
- Seçenekler: `--chunk=500` (görev başına kayıt), `--dry-run` (yalnızca önceki bir anahtarı kullanan kayıtları sayar), `--force` (onay yok), `--actor=`.
- Denetim: kaydedilir (toplu iş kimliği, görev sayısı / önizleme sayısı)
- Doğrulama: görevleri Flower'da izleyin. Bittiklerinde ve `--dry-run` 0 bildirdiğinde önceki anahtarı `PII_PREVIOUS_KEYS` içinden kaldırın.
- Örnek

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu
  ```

## Yerelleştirme (Aşama 0)

### `i18n_missing`

- Amaç: çevrilebilir metinleri kaynaktan `makemessages` gibi (dosya yazmadan) çıkarır, bunları her katalogla (genel `locale/` ve her uygulamanın `locale/` dizini) karşılaştırır ve dil başına eksik metinleri (katalogda yok, boş `msgstr`, fuzzy, farklı yer tutucular) ve eskimiş girdileri listeler.
- Argümanlar/seçenekler: `[locale]` (yalnızca bir dil, örn. `ko`, `zh-hans`, `lo`), `--strict` (metin eksikse çıkış kodu 2; CI'da kullanılır), `--no-extract` (yalnızca katalogları kontrol eder, kaynak taraması yok).
- Denetim: kaydedilmez
- Gereksinim: GNU gettext (`xgettext`, `msguniq`).
- Örnek

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- Amaç: çevirmenler için bir tablo yazar (`.xlsx` veya `.csv`, uzantıya göre seçilir). Sütunlar: `catalog` (katalog konumu), `context`, `source` (İngilizce msgid), `source_plural`, `translation`, `note` (özgün anahtar).
- Argümanlar/seçenekler: `{locale} {path}`, `--missing` (yalnızca çevirisi olmayan metinler).
- Denetim: kaydedilmez
- Örnek: `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- Amaç: çevirmenlerin doldurduğu bir tabloyu kataloglara (`.po`) geri yazar ve derler (`.mo`). Yalnızca kataloglarda bulunan metinler (aynı katalog, bağlam ve İngilizce metin) içe aktarılır; boş çeviriler atlanır.
- Argümanlar/seçenekler: `{locale} {path}`, `--dry-run` (yazılacak metinleri listeler), `--actor=`.
- Denetim: kaydedilir (dil, çeviri sayısı)
- Not: kataloglar depoda bulunur. Bir içe aktarmadan sonra `.po` değişikliklerini commit edin.

### `i18n_makemessages`

- Amaç: her kataloğun kaynakla eşleşmesi için `makemessages` komutunu depo kökünden çalıştırır (ko, zh_Hans, lo). Metinler, uygulamanın kendi `locale/` dizini varsa oraya, yoksa genel `locale/` dizinine gider. `.venv`, `tests`, `docs` ve benzeri dizinler atlanır.
- Seçenekler: Django `makemessages` gibi (`-l`, `--no-obsolete`, ...).
- Denetim: kaydedilmez
- Örnek: `uv run manage.py i18n_makemessages`

## Kontroller (Aşama 0)

### `pdf_sample`

- Amaç: yazı tiplerini ve PDF hizmetine (Gotenberg) bağlantıyı kontrol etmek için Hangıl, CJK, Lao, Tay, Devanagari, Kiril ve Latin yazılarını karıştıran bir tabloyu PDF'e dönüştürür.
- Argüman: `[path]` (varsayılan `pdf-sample.pdf`, özel dosya deposu `PRIVATE_MEDIA_ROOT` dizinine göre).
- Denetim: kaydedilmez
- Başarısızlıkta: çıkış kodu 1. Bağlantı hatalarında `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` değerlerini ve Gotenberg konteynerini kontrol edin.
- Örnek: `uv run manage.py pdf_sample`

### `naming_check`

- Amaç: veritabanı şemasını ve kaynakları [adlandırma kurallarına](../../../development/naming.md) göre kontrol eder. Gerçek veritabanı kataloğundaki (şemalar `public`, `audit`, `reporting`) tablo ve sütun adlarını, Ninefruits uygulamalarının migration dosya adlarını, yönetim komutu adlarını (`context_action`) ve çeviri kataloglarının (`.po`) msgid ve msgctxt değerlerini kontrol eder.
- Kurallar: snake_case, yasak son ekler (`_old`, `_new`, `_backup`, `_tmp`, tarihler, sayılar), dil kodu içeren adlar, saat dilimi olmayan zaman sütunları (`timestamp without time zone`), mantıksal (boolean) sütun adları (`is_`, `has_`, `can_` veya bir fiil), tarih sütunu adları (`_date`), anlamsal anahtar biçimindeki msgid'ler (`registration.errors.x`). Django ve paketler tarafından tanımlanan tablolar (`django_*`, allauth, Celery beat, `settings`, `cache`, `jobs`, `media` vb.) hariç tutulur.
- Seçenekler: `--database=` (kontrol edilecek veritabanı bağlantısı, varsayılan `default`), `--skip-database` (yalnızca dosya kontrolleri, veritabanı yok).
- Denetim: kaydedilmez
- Çıkış kodu: sorun bulunduğunda 2.
- Örnek

  ```bash
  uv run manage.py naming_check
  ```

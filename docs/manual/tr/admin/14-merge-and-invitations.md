# 14. Kişileri birleştirme ve hesap davetleri

Menü: **Öğrenciler ve personel > Kişiler**, ardından bir kişinin ayrıntı sayfasının üstündeki **Mükerrer kaydı birleştir** ve **Hesap oluşturmaya davet et**

## Mükerrer kişileri birleştirme

Aynı insan iki kişi olarak kaydedildiğinde kullanılır (örneğin mevcut kişinin bulunamadığı ve yeni bir kişinin oluşturulduğu bir yeniden kayıt). `Mükerrer kişileri birleştirme` yetkisi gerekir.

1. Adayları bulun: kişi listesinde aynı ad ve doğum tarihini veya aynı kimlik numarasını arayın. BT operatörü `uv run manage.py people_find_duplicates` ile tam bir aday listesi çıkarabilir.
2. **Kaldırılacak kişinin (mükerrer kaydın)** ayrıntı sayfasında **Mükerrer kaydı birleştir** düğmesine basın, **Bu kişiyi koru** altında kişiyi listeden seçin ve bir gerekçe girin. Birleştirme tamamlandığında korunan kişinin sayfasına yönlendirilirsiniz.
3. Kaldırılan kişinin öğrenci kayıtları, başvuruları, öğretim elemanı bilgileri, velileri ve hesabı korunan kişiye taşınır. Her ikisinin de hesabı varsa kaldırılan kişinin hesabı devre dışı bırakılır ve bağlı kurumsal oturum açma bilgisi mümkünse taşınır.
4. Kaldırılan kişi, eski kayıtlar hâlâ bulunabilsin diye **Birleştirilmiş** olarak kalır (liste filtresi **Birleştirilmiş**). Yeni öğrenci kayıtları için kullanılamaz.

- Her iki kişinin de öğretim elemanı bilgileri varsa birleştirme reddedilir. Önce öğretim elemanı bilgilerini düzenleyin.
- Her iki kişinin de aynı başvuru döneminde açık bir başvurusu varsa birleştirme reddedilir. Adaydan birini geri çekmesini isteyin.
- **Bu işlem geri alınamaz.** Birleştirmeden önce öğrenci kayıtlarını ve doğum tarihini mutlaka kontrol edin. Birleştirme, gerekçesiyle birlikte işlem günlüğüne yazılır.

## Hesap davetleri

CSV ile yüklenen öğrenciler ve öğretim elemanları gibi hesabı olmayan kişilere davet e-postası gönderir. `Kişileri hesap oluşturmaya davet etme` yetkisi gerekir.

1. Kişinin ayrıntı sayfasında **Hesap oluşturmaya davet et** düğmesine basın ve oturum açma e-postasını (genellikle kişisel bir e-posta) girin.
2. Alıcı, e-postadaki bağlantı üzerinden bir parola belirlediğinde hesap oluşturulur ve hemen oturum açılır.

- Bağlantı, **Ayarlar > Öğrenci kayıtları > Davet bağlantılarının geçerlilik süresi (gün)** boyunca geçerlidir (varsayılan 14 gün).
- Yeniden göndermek önceki bağlantıyı geçersiz kılar.
- Zaten hesabı olan bir kişiyi davet edemez veya başka bir hesabın kullandığı bir e-postayı kullanamazsınız.
- Mezuniyetten sonra aynı hesap korunur. Yalnızca kurumsal e-postasını kullanan kişilerden oturum açma e-postalarını kişisel bir adresle değiştirmelerini isteyin ([bölüm 15](15-sign-in-methods.md)).

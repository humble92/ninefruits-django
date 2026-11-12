# 5. Kurum ayarları ve ilk kurulum sırası

## Kurum ayarları

**Ayarlar > Kurum** altında ayarlanır (`Kurum ayarlarını yönetme` yetkisi).

| Ayar | Açıklama |
|---|---|
| Kurum adı | Her dil için girilir. Yönetim panelinin sol üst köşesinde gösterilir |
| Saat dilimi | Dönem tarihlerinin ve işlem aralıklarının değerlendirilmesinde esas alınır, örneğin `Asia/Seoul`. Kaydedilen her zaman bu saat diliminde gösterilir |
| Sunulan diller | Kullanıcıların seçebileceği diller. Listede yalnızca çeviri dosyaları yüklü olan diller görünür |
| Varsayılan dil | Dil seçmemiş kullanıcılar için ve tarayıcı dili bilinmediğinde kullanılır |

## Yeni bir üniversite için ilk kurulum sırası

BT operatörü `setup_install` işlemini tamamladıktan sonra (işletim kılavuzu, [Kurulum](../operations/installation.md)) iş yöneticisi verileri aşağıdaki sırayla girer. Sonraki adımlar önceki adımlardaki kodlara başvurduğu için sırayı koruyun.

1. **Kurum ayarları**: ad, saat dilimi, diller (bu bölüm)
2. **Kod verileri**: etnik köken, giriş türü ve derslik türü değerleri ([bölüm 6](06-code-data.md)). Kurulum sırasında Kore üniversitesi profili uygulandıysa derslik türleri zaten mevcuttur.
3. **Birim türleri** listesini kontrol edin, ardından **Birimler**: üniversite → fakülte → bölüm ([bölüm 7](07-org-units-and-programs.md)). Çok sayıda birim için CSV kullanın ([bölüm 9](09-csv-import.md)).
4. **Programlar**: bölümlere göre derece programları ([bölüm 7](07-org-units-and-programs.md))
5. **Binalar**, **Derslikler** ([bölüm 8](08-facilities.md), CSV kullanılabilir)
6. **Dönem türleri** ve **Ders saatleri** listelerini kontrol edin ([bölüm 10](10-terms.md))
7. **Ders türleri** ve **Not ölçekleri** listelerini kontrol edin. Bir varsayılan ölçek belirlenmelidir ([bölüm 11](11-course-categories-and-grade-scales.md))
8. **Akademik yıllar** → **Dönemler** → her dönem için **İşlem aralıkları** ([bölüm 10](10-terms.md))
9. **Kullanıcılar ve erişim**: bölüm sekreterleri gibi birim kapsamı gerektiren roller artık kapsam hedefi olarak bölümü seçebilir ([bölüm 2](02-users-and-roles.md))

Veriler girildiğinde BT operatöründen işlem aralıklarını `uv run manage.py term_inspect` ile kontrol etmesini isteyin.

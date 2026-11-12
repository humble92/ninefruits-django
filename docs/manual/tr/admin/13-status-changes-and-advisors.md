# 13. Durum değişiklikleri ve danışmanlar

Menü: **Öğrenciler ve personel > Durum değişiklikleri**, **Durum değişikliği türleri** ve bir öğrenci kaydındaki **Durum değişiklikleri** ve **Danışmanlar** sekmeleri

## Öğrenci durumu

| Durum | Anlamı |
|---|---|
| Kayıtlı | Ders kaydı yapabilir |
| Kayıt donduruldu | Kayıt korunur, ders kaydı yapamaz |
| Kendi isteğiyle ayrıldı, İlişiği kesildi | Kayıt sona ermiştir. Yeniden kayıt yeni bir öğrenci kaydı oluşturur |
| Mezun | Mezuniyet tarihi zorunludur. Hesap, mezun erişimiyle korunur |

Kayıtlı ve kayıt donduruldu durumları "mevcut öğrenci" sayılır (öğrenci numarasıyla oturum açma, danışman ataması vb.).

## Durum değişikliği türleri

Her tür **Yeni durum**, **İzin verilen önceki durumlar** ve **Öğrenciler talep edebilir** seçeneklerini tanımlar. Kurulum; kayıt dondurma, kayıt dondurma sonrası dönüş, kendi isteğiyle ayrılma, ilişik kesme, yeniden kayıt ve mezuniyet türlerini oluşturur. Adlar değiştirilebilir ve değiştirilen adlar yeniden kurulumda korunur.

## Öğrenci talepleri ve onay

1. Öğrenci, portaldaki **Kayıtlarım** altında tür, geçerlilik tarihi ve gerekçeyle bir talep gönderir. Bir kaydın aynı anda yalnızca bir bekleyen talebi olabilir ve öğrenci, karar verilmeden önce talebi iptal edebilir.
2. Personel talebi **Durum değişiklikleri** listesinde (varsayılan: bekleyenler) **Onayla** veya **Reddet** ile karara bağlar. Ret için bir not zorunludur. Her satırın işlem menüsünü kullanın; not bir pencerede istenir.
3. Onaylandığında kaydın durumu hemen değişir ve değişiklik geçmişe eklenir.

- `Durum değişikliklerini onaylama ve kaydetme` yetkisi gerekir; yalnızca yetki kapsamındaki (birim, program) kayıtlar için karar verilebilir.
- Kendi gönderdiğiniz bir talebi onaylayamazsınız (görevler ayrılığı).
- Talep yapıldıktan sonra kaydın durumu değiştiyse (örneğin kayıt dondurma başka bir yolla zaten kaydedildiyse) talep onaylanamaz. Talebi reddedin ve yeni bir talep isteyin.

## Personel tarafından doğrudan kayıt

İlişik kesme, kâğıt üzerinde alınan talepler ve benzeri durumlar, öğrenci kaydındaki **Durum değişikliği kaydet** ile doğrudan kaydedilir. Gerekçe zorunludur ve kaydı yapan kişi onaylayan olarak saklanır. `Durum değişikliklerini onaylama ve kaydetme` yetkisi gerekir.

Her değişiklik işlem günlüğüne ve veri değişikliklerine yazılır ([bölüm 4](04-audit.md)).

## Danışmanlar

Öğrenci kaydındaki **Danışman ata** altında öğretim elemanını, rolü (Birincil danışman, Eş danışman) ve başlangıç tarihini seçin (`Danışman atama` yetkisi).

- Tek bir birincil danışman vardır. Yeni bir birincil danışman atamak önceki atamayı başlangıç tarihinden bir gün önce sonlandırır ve geçmişi korur.
- Yalnızca görevdeki öğretim elemanları seçilebilir.
- Danışmanlar mevcut danışmanlık öğrencilerini portaldaki **Danışmanlık öğrencilerim** altında görür ve bu öğrencilerin kayıtlarını görüntüleyebilir.

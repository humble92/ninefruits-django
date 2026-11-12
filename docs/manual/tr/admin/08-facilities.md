# 8. Binalar ve derslikler

Menü: **Temel veriler > Binalar**, **Derslikler** (`Binaları ve derslikleri yönetme` yetkisi)

## Binalar

Kodu (örneğin `SCI`), adı (her dil için) ve adresi girin. Dersliği olan bir bina silinemez; bu nedenle artık kullanılmadığında **Etkin** seçeneğini kapatın.

## Derslikler

| Alan | Açıklama |
|---|---|
| Bina, Derslik numarası | Derslik numaraları bir bina içinde benzersizdir, örneğin `101` |
| Ad | İsteğe bağlı, örneğin Büyük Konferans Salonu |
| Derslik türü | `room_type` kod listesinden bir değer (derslik, laboratuvar vb.) |
| Birim | Dersliği yöneten bölüm (isteğe bağlı) |
| Kapasite | Ders programları hazırlanırken şube kontenjanıyla karşılaştırılır ([18. bölüm](18-sections-and-timetables.md)) |
| Ders programında kullanılır | Kapalıyken derslik, ders programları hazırlanırken dışarıda bırakılır (ofisler, depolar vb.) |

Çok sayıda derslik için [CSV içe aktarma](09-csv-import.md) kullanın. Önce binaların kaydedilmiş olması gerekir.

# 6. Kod verileri, ülkeler, diller

Menü: **Temel veriler > Kod listeleri**, **Ülkeler**, **Diller** (`Kod verilerini, ülkeleri ve dilleri yönetme` yetkisi)

## Kod verileri

Üniversiteden üniversiteye farklılık gösteren kısa listeler. Her listenin (türün) kod değerleri vardır.

| Liste kodu | Amaç | Eski sistem (YUSTIC) |
|---|---|---|
| `ethnicity` | Etnik köken | `FNATION` |
| `admission_type` | Giriş türü | `FADMDIST` |
| `room_type` | Derslik türü | `ROOM.FORWHAT` |

- Sistem listeleri (yukarıdaki üç liste) uygulamada koduyla arandığı için liste kodları değiştirilemez veya silinemez. Değerler serbestçe eklenebilir.
- Bir listeyi açın ve aşağıdaki **Kodlar** bölümüne değer ekleyin. Kodlar küçük harf, rakam ve alt çizgiden oluşur (örneğin `korean`). Adı her dil için girin; İngilizce ad zorunludur.
- Artık kullanılmayan değerleri silmeyin; bunun yerine **Etkin** seçeneğini kapatın. Bir değer, veriler tarafından hâlâ kullanılıyorsa silinemez.
- Çok sayıda değeri [CSV içe aktarma](09-csv-import.md) ile girin.

## Ülkeler ve diller

ISO standart listeleri (249 ülke, yaklaşık 180 dil) kurulum sırasında yüklenir. Adlar, yüklü diller için otomatik olarak doldurulur.

- Ekranda gösterilen adı değiştirmek için **Düzenle** altında değiştirin. Değiştirilen ad sonraki sistem güncellemelerinde korunur.
- Bir girdiyi seçim listelerinden gizlemek için **Etkin** seçeneğini kapatın.

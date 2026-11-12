# 11. Ders türleri ve not ölçekleri

## Ders türleri

Menü: **Temel veriler > Ders türleri** (`Ders türlerini yönetme` yetkisi). Eski sistemin (YUSTIC) `SFOBJDIST` yapısının yerini alır.

Genel eğitim zorunlu veya alan seçmeli gibi derslerin sınıflandırması. Türler bir **Üst** belirlenerek gruplanabilir (örneğin Genel eğitim → Genel eğitim zorunlu, Genel eğitim seçmeli). Mezuniyet koşulları ([17. bölüm](17-courses-and-curriculum.md), [26. bölüm](26-graduation.md)) "alan zorunlu derslerinden 30 kredi" gibi bu türlere başvurur.

## Not ölçekleri

Menü: **Temel veriler > Not ölçekleri** (`Not ölçeklerini yönetme` yetkisi). Eski sistemin `SSCOREDEF` yapısının yerini alır.

| Ölçek alanı | Açıklama |
|---|---|
| En yüksek not katsayısı | Örneğin 4.5 |
| Varsayılan | Yalnızca bir ölçek varsayılan olabilir. Yalnızca hiçbir ölçek varsayılan değilken açılabilir (aşağıya bakın) |

Bir ölçeği açın ve aşağıdaki **Notlar** bölümüne not ekleyin.

| Not alanı | Açıklama |
|---|---|
| Not | Örneğin `A+`, `P` |
| Not katsayısı | Ortalamaya katılan notlar için zorunludur |
| Başlangıç/Bitiş (%) | Ham puan dönüşüm aralıkları (isteğe bağlı), örneğin A+ 95–100 |
| Ortalamaya katılır | P/NP gibi not ortalamasının dışında tutulan notlar için kapatın |
| Geçer not | F veya NP gibi kredi kazandırmayan notlar için kapatın |
| Uygulandığı dersler | Notlu dersler (harf notları), Başarılı/başarısız dersler (P, NP) veya Her ikisi (örneğin I, eksik). Not giriş ekranı yalnızca dersin notlandırma esasına uyan notları gösterir |

**Varsayılan ölçek kurulumda belirlenir ve değiştirilemez** (2026-10-23 tarihli karar); çünkü her not ve not ortalaması bu ölçekle ifade edilir. Ölçeği `setup_install --grade-scale=4.5|4.3` ile ayarlayın; seçenek verilmezse ilk profilin ölçeği varsayılan olur. Varsayılan işareti ekranda değiştirilemez ve varsayılan ölçek silinemez. Notlara göre puan aralıkları ve not katsayıları bu ekranda düzenlenir ([bölüm 21](21-grades.md)).

Profillerin yüklediği ölçekler

- Kore üniversitesi: 4.5 ölçeği (`KR45`): A+ 4.5 (95–100), A0 4.0 (90–), B+ 3.5 (85–), B0 3.0 (80–), C+ 2.5 (75–), C0 2.0 (70–), D+ 1.5 (65–), D0 1.0 (60–), F 0, P, NP
- `--grade-scale=4.3` veya eski YUST profili: 4.3 ölçeği (`KR43` veya `YUST43`): A+ 4.3 (97–100), A0 4.0 (93–), A- 3.7 (90–), B+ 3.3 (87–), B0 3.0 (83–), B- 2.7 (80–), C+ 2.3 (77–), C0 2.0 (73–), C- 1.7 (70–), D+ 1.3 (67–), D0 1.0 (63–), D- 0.7 (60–), F 0, P, NP (eski profil ayrıca N ve I notlarını da içerir). Puan aralıkları 3 puanlık aralıklarla başladığından okulun standardına göre ayarlayın.

Notlarda kullanılmış bir ölçek silinemez.

# 7. Birimler ve programlar

Menü: **Temel veriler > Birim türleri**, **Birimler**, **Programlar**

## Birimler

Üniversiteler, fakülteler, bölümler, ana dallar ve idari birimler tek bir ekranda yönetilir. Bunlar eski sistemin (YUSTIC) fakültelerinin (`SFCOLLEGE`) ve bölümlerinin (`SFDEPARTMENT`) yerini alır.

| Alan | Açıklama |
|---|---|
| Kod | Kalıcı bir tanımlama kodu, örneğin `CSE` |
| Tür | Üniversite, fakülte, bölüm vb. (Birim türleri ekranında yenileri eklenebilir) |
| Ad, Kısa ad | Her dil için |
| Üst birim | Bu birimin bağlı olduğu birim. Bir birim kendi altına veya kendi alt birimlerinden birinin altına taşınamaz |
| Geçerlilik başlangıcı, Geçerlilik bitişi | Birimin var olduğu süre. Boş bir bitiş tarihi, birimin hâlâ faaliyette olduğu anlamına gelir |

- Liste varsayılan olarak **Yalnızca şu an geçerli olanlar** filtresiyle gösterilir. Geçmiş birimleri de görmek için filtreyi kapatın.
- Bir rol atamasının kapsamı olarak bir birim seçildiğinde onun altındaki tüm birimler dahil olur. Örnek: Mühendislik Fakültesi kapsamı = Mühendislik Fakültesi'ndeki tüm bölümler.

## Yeniden yapılanmalar

Geçmiş öğrenci kayıtları ve notlar, birimin o tarihteki hâline işaret etmelidir; bu nedenle bir birim yerinde düzenlenmez, bunun yerine değişiklik bir **yeniden yapılanma** olarak kaydedilir.

1. Ortadan kalkan (veya değişen) birimin **Düzenle** sayfasını açın.
2. **Yeniden yapılandır** düğmesine basın.
3. Değişiklik türünü seçin.
   - **Adı değiştirildi**: önce yeni adla birimi oluşturun ve onu halef birim olarak belirleyin
   - **Birleştirildi**: birkaç birim tek birimde birleştiğinde her birimden aynı halef birimi belirleyin
   - **Bölündü**: bir birim birkaç birime ayrıldığında birden fazla halef birim belirleyin
   - **Bağlılığı değiştirildi**: birim yeni bir birim olarak farklı bir üst birimin altına geçtiğinde
4. **Geçerlilik tarihi** ve bir gerekçe girin. Birim, geçerlilik tarihinden bir gün önce sona erer ve kayıt aşağıdaki **Halef birimler** listesinde görünür.

Basit bir yazım hatası, yeniden yapılanmayla değil adın **düzenlenmesiyle** düzeltilir (veri değişikliği kaydedilir).

## Programlar

Derece programları veya ana dal programları. Öğrenci kayıtları bir programa bağlıdır ([12. bölüm](12-people-and-student-records.md)).

| Alan | Açıklama |
|---|---|
| Kod, Ad, Derece adı | Derece adı örneği: Mühendislik Lisansı |
| Öğrenim düzeyi | Ön lisans, Lisans, Yüksek lisans, Doktora, Sertifika, Derecesiz |
| Birim | Programı yürüten bölüm |
| Normal öğrenim süresi | Tamamlama için standart süre (yıl) |
| Geçerlilik başlangıcı, Geçerlilik bitişi | Programın var olduğu süre; yeni öğrenci kabul ettiği süre değildir |
| Çift ana dal kabul eder, Yan dal kabul eder | Diğer programların öğrencilerinin bu programa çift ana dal veya yan dal olarak başvurup başvuramayacağı ([bölüm 19](19-second-majors-and-minors.md)) |

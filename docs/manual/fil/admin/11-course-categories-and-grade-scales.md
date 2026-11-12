# 11. Mga kategorya ng asignatura at iskala ng marka

## Mga kategorya ng asignatura

Menu: **Sangguniang datos > Mga kategorya ng asignatura** (pahintulot na `Pamahalaan ang mga kategorya ng asignatura`). Pinapalitan ang `SFOBJDIST` ng lumang sistema (YUSTIC).

Ang klasipikasyon ng mga asignatura, gaya ng kinakailangang general education o elective sa major. Maaaring pagpangkatin ang mga kategorya sa pamamagitan ng pagtatakda ng **Magulang** (halimbawa General education → Kinakailangang general education, Elective na general education). Tumutukoy sa mga ito ang mga kinakailangan sa pagtatapos ([kabanata 17](17-courses-and-curriculum.md), [kabanata 26](26-graduation.md)), gaya ng "30 units ng mga kinakailangang asignatura sa major".

## Mga iskala ng marka

Menu: **Sangguniang datos > Mga iskala ng marka** (pahintulot na `Pamahalaan ang mga iskala ng marka`). Pinapalitan ang `SSCOREDEF` ng lumang sistema.

| Field ng iskala | Paglalarawan |
|---|---|
| Pinakamataas na grade point | Halimbawa 4.5 |
| Default | Isang iskala lamang ang maaaring maging default. Maaari lamang itong i-on habang walang iskalang default (tingnan sa ibaba) |

Buksan ang isang iskala at magdagdag ng mga marka sa **Mga marka** sa ibaba.

| Field ng marka | Paglalarawan |
|---|---|
| Marka | Halimbawa `A+`, `P` |
| Grade point | Kinakailangan para sa mga markang ibinibilang sa GPA |
| Mula/Hanggang (%) | Mga saklaw ng conversion ng raw score (opsiyonal), halimbawa A+ 95–100 |
| Ibinibilang sa GPA | I-off para sa mga markang hindi isinasama sa GPA, gaya ng P/NP |
| Pasado | I-off para sa mga markang hindi nagbibigay ng units, gaya ng F o NP |
| Para sa | Mga asignaturang may marka (letter grade), Mga asignaturang pasado/bagsak (P, NP) o Pareho (halimbawa I, incomplete). Ipinapakita lamang ng screen ng pagpasok ng marka ang mga markang tumutugma sa batayan ng pagmamarka ng asignatura |

**Itinatakda ang default na iskala sa pag-install at hindi na ito mababago** (pasya noong 2026-10-23), dahil ipinapahayag sa iskalang iyon ang bawat marka at GPA. Itakda ito gamit ang `setup_install --grade-scale=4.5|4.3`; kapag walang option, ang iskala ng unang profile ang nagiging default. Hindi mababago sa screen ang flag na default at hindi mabubura ang default na iskala. Ang mga saklaw ng iskor at grade point bawat marka ay ine-edit sa screen na ito ([kabanata 21](21-grades.md)).

Mga iskalang nilo-load ng mga profile

- Unibersidad sa Korea: iskalang 4.5 (`KR45`): A+ 4.5 (95–100), A0 4.0 (90–), B+ 3.5 (85–), B0 3.0 (80–), C+ 2.5 (75–), C0 2.0 (70–), D+ 1.5 (65–), D0 1.0 (60–), F 0, P, NP
- `--grade-scale=4.3` o ang lumang profile ng YUST: iskalang 4.3 (`KR43` o `YUST43`): A+ 4.3 (97–100), A0 4.0 (93–), A- 3.7 (90–), B+ 3.3 (87–), B0 3.0 (83–), B- 2.7 (80–), C+ 2.3 (77–), C0 2.0 (73–), C- 1.7 (70–), D+ 1.3 (67–), D0 1.0 (63–), D- 0.7 (60–), F 0, P, NP (kasama rin sa lumang profile ang N at I). Nagsisimula ang mga saklaw ng iskor sa pagitang 3 puntos, kaya iangkop ang mga ito sa pamantayan ng paaralan.

Hindi mabubura ang iskalang nagamit na sa mga marka.

# 5. Mga setting ng institusyon at pagkakasunod-sunod ng unang pag-set up

## Mga setting ng institusyon

Itinatakda sa **Mga setting > Institusyon** (pahintulot na `Pamahalaan ang mga setting ng institusyon`).

| Setting | Paglalarawan |
|---|---|
| Pangalan ng institusyon | Inilalagay sa bawat wika. Ipinapakita sa kaliwang itaas ng panel ng administrasyon |
| Time zone | Ang batayan sa pagtukoy ng mga petsa ng termino at mga takdang panahon ng termino, halimbawa `Asia/Seoul`. Ipinapakita sa time zone na ito ang lahat ng nakaimbak na oras |
| Mga iniaalok na wika | Mga wikang mapipili ng mga user. Ang mga wikang may naka-install na translation file lamang ang lumalabas sa listahan |
| Default na wika | Ginagamit para sa mga user na hindi pa pumili ng wika at kapag hindi alam ang wika ng browser |

## Pagkakasunod-sunod ng unang pag-set up para sa bagong unibersidad

Matapos makumpleto ng IT operator ang `setup_install` (manwal ng operasyon, [Pag-install](../operations/installation.md)), naglalagay ang administrator ng negosyo ng datos ayon sa pagkakasunod-sunod sa ibaba. Tumutukoy ang mga susunod na hakbang sa mga code mula sa mga naunang hakbang, kaya sundin ang pagkakasunod-sunod.

1. **Mga setting ng institusyon**: pangalan, time zone, mga wika (kabanatang ito)
2. **Mga code**: mga halaga ng etnisidad, uri ng admisyon at uri ng silid ([kabanata 6](06-code-data.md)). Kung inilapat ang profile ng unibersidad sa Korea sa pag-install, mayroon nang mga uri ng silid.
3. Suriin ang **Mga uri ng yunit ng organisasyon**, saka ang **Mga yunit ng organisasyon**: unibersidad → kolehiyo → departamento ([kabanata 7](07-org-units-and-programs.md)). Para sa maraming yunit, gumamit ng CSV ([kabanata 9](09-csv-import.md)).
4. **Mga programa**: mga degree program bawat departamento ([kabanata 7](07-org-units-and-programs.md))
5. **Mga gusali**, **Mga silid** ([kabanata 8](08-facilities.md), maaaring CSV)
6. Suriin ang **Mga uri ng termino** at **Mga period ng klase** ([kabanata 10](10-terms.md))
7. Suriin ang **Mga kategorya ng asignatura** at **Mga iskala ng marka**. Kailangang may isang itinakdang default na iskala ([kabanata 11](11-course-categories-and-grade-scales.md))
8. **Mga taong akademiko** → **Mga termino** → **Mga takdang panahon ng termino** bawat termino ([kabanata 10](10-terms.md))
9. **Mga user at access**: ang mga tungkuling nangangailangan ng saklaw na yunit ng organisasyon, gaya ng Katuwang ng Departamento, ay maaari nang pumili ng departamento bilang target ng saklaw ([kabanata 2](02-users-and-roles.md))

Kapag nailagay na ang datos, hilingin sa IT operator na suriin ang mga takdang panahon ng termino gamit ang `uv run manage.py term_inspect`.

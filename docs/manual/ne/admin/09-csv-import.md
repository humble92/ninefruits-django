# 9. CSV आयात

संगठन एकाइ, कार्यक्रम, भवन, कोठा र कोड सूचीका स्क्रिनको माथिपट्टिको **CSV आयात गर्नुहोस्** बटन प्रयोग गर्नुहोस् (`CSV बाट सन्दर्भ डेटा आयात गर्ने` अनुमति)। विद्यार्थी अभिलेख, प्राध्यापक, विषय र दर्ता रोकहरू पनि यसै गरी आयात गरिन्छन् (तल हेर्नुहोस्)। धेरै ठूला फाइलहरू IT सञ्चालकले `reference_import` कमान्डले यसै गरी आयात गर्न सक्छन्।

## साझा नियमहरू

- पहिलो पङ्क्तिमा स्तम्भका नामहरू हुन्छन् (तलका तालिका)। इन्कोडिङ UTF-8 हो; Excel मा "CSV UTF-8" का रूपमा सुरक्षित गर्नुहोस्।
- कोड पहिल्यै भएको पङ्क्तिले त्यो अभिलेख **अद्यावधिक** गर्छ। एउटै फाइल फेरि आयात गर्दा दोहोरो बन्दैन।
- भाषाअनुसारका स्तम्भ `स्तम्भ_भाषा` ढाँचामा हुन्छन्: `name_en`, `name_ko`, `name_zh-hans`। नयाँ पङ्क्तिमा अङ्ग्रेजी नाम (`name_en`) अनिवार्य छ। खाली सेलले विद्यमान अनुवाद मेटाउँदैन।
- मिति `2026-03-01` ढाँचामा; हो/होइन `1`/`0` वा `true`/`false` का रूपमा लेखिन्छ।
- पहिले हेडर जाँचिन्छ (कुनै अनिवार्य स्तम्भ छुटेमा केही पनि आयात हुँदैन)। 500 पङ्क्तिसम्मका फाइलहरू तुरुन्तै आयात हुन्छन्; ठूला फाइलहरू पृष्ठभूमिमा (Celery) प्रशोधन हुन्छन्। नतिजा **सन्दर्भ डेटा > CSV आयातहरू** अन्तर्गतको आयात पृष्ठमा देखिन्छ (आयात गरिएका पङ्क्ति, असफल पङ्क्ति र तिनका कारण)। कुनै पङ्क्ति असफल भएमा, **असफल पङ्क्तिहरू डाउनलोड गर्नुहोस्** ले प्रत्येक पङ्क्तिको कारणसहित CSV दिन्छ। त्यसलाई सच्याएर त्यो फाइल मात्र फेरि आयात गर्नुहोस्।
- स्तम्भका नामहरू तलका तालिकासँग मेल खानुपर्छ; अज्ञात स्तम्भहरूलाई बेवास्ता गरिन्छ। मूल प्रणालीको `name_zh_CN` स्तम्भ नामलाई `name_zh-hans` का रूपमा स्वीकार गरिन्छ।

## स्तम्भको ढाँचा

| प्रकार | अनिवार्य स्तम्भ | वैकल्पिक स्तम्भ |
|---|---|---|
| संगठन एकाइ | `code`, `type` (संगठन एकाइको प्रकारको कोड), `name_en`, `effective_start_date` | `parent` (माथिल्लो एकाइको कोड), `name_ko` आदि, `short_name_*`, `effective_end_date`, `sort_order` |
| कार्यक्रम | `code`, `org_unit` (संगठन एकाइको कोड), `degree_level`, `name_en`, `effective_start_date` | `degree_title_*`, `standard_duration_years`, `effective_end_date`, `allows_second_major`, `allows_minor` |
| भवन | `code`, `name_en` | `name_*`, `address`, `is_active` |
| कोठा | `building` (भवनको कोड), `code` (कोठा नम्बर) | `name_*`, `room_type` (कोठाको प्रकारको कोड), `org_unit`, `capacity`, `is_schedulable`, `is_active` |
| कोड मान | `type` (सूची कोड), `code`, `name_en` | `name_*`, `sort_order`, `is_active` |

`degree_level` का मानहरू: `associate`, `bachelor`, `master`, `doctorate`, `certificate`, `non_degree`

संगठन एकाइमा माथिल्ला एकाइहरू पहिले आउनुपर्छ (विश्वविद्यालय → सङ्काय → विभागको क्रममा मिलाउनुहोस्)।

## उदाहरण: संगठन एकाइ

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## विद्यार्थी र प्राध्यापक

विद्यार्थी अभिलेखहरू `student_number` द्वारा र प्राध्यापकहरू `employee_number` द्वारा मिलाइन्छन् र अद्यावधिक गरिन्छन्। दुवैले व्यक्तिका स्तम्भहरू साझा गर्छन्।

| प्रकार | नयाँ पङ्क्तिका अनिवार्य स्तम्भ | वैकल्पिक स्तम्भ |
|---|---|---|
| विद्यार्थी अभिलेख | `student_number`, `program` (कार्यक्रम कोड), `admission_date`, `family_name` | `catalog_year` (खाली भएमा भर्ना वर्ष), `year_level`, `status`, `graduation_date`, `institutional_email` |
| प्राध्यापक | `employee_number`, `org_unit` (संगठन एकाइको कोड), `employment_type`, `family_name` | `academic_title_*`, `hire_date`, `end_date` |
| व्यक्तिका स्तम्भ (साझा) | — | `given_name`, `name_ko` जस्ता भाषाअनुसारका नाम, `birth_date`, `gender`, `email`, `phone`, `national_id` |

- `status` का मानहरू: `enrolled`, `on_leave`, `withdrawn`, `dismissed`, `graduated` (graduated का लागि `graduation_date` अनिवार्य)। आयातद्वारा परिवर्तन गरिएको स्थितिलाई **डेटा सुधार** मानिन्छ र अभिलेख स्थिति परिवर्तनको इतिहास बन्दैन। वास्तविक परिवर्तनहरू स्क्रिनमा अभिलेख गरिन्छन् ([अध्याय 13](13-status-changes-and-advisors.md))।
- `employment_type` का मानहरू: `full_time`, `part_time`, `adjunct`, `visiting`, `emeritus`। `gender` का मानहरू: `female`, `male`, `other`, `undisclosed`।
- नयाँ विद्यार्थी अभिलेखको `national_id` विद्यमान व्यक्तिसँग मिलेमा, अभिलेख त्यही व्यक्तिमा जोडिन्छ (पुनर्भर्ना)। नमिलेमा नयाँ व्यक्ति बनाइन्छ। अद्यावधिक गर्दा खाली सेलले विद्यमान मान मेटाउँदैन।
- आयात गरिएका विद्यार्थी र प्राध्यापकको खाता हुँदैन। [खाता निमन्त्रणा](14-merge-and-invitations.md#खाता-निमन्त्रणा) बाट उनीहरूलाई निमन्त्रणा पठाउनुहोस्।

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

विषय संस्करणको आयात [अध्याय 17](17-courses-and-curriculum.md) मा, दर्ता रोकको आयात [अध्याय 20](20-registration.md) मा वर्णन गरिएको छ।

## दर्ता रोक

**विषय दर्ता > रोकहरू** सूचीको माथिपट्टिको **CSV आयात गर्नुहोस्** (`रोक लगाउने र हटाउने, नियम छुट दिने` अनुमति) वा `uv run manage.py reference_import registration_holds`। पुरानो `SRDENY` डेटा वा आर्थिक प्रशासन कार्यालयको शुल्क नतिरेका विद्यार्थीको सूची लोड गर्न प्रयोग गरिन्छ।

| अनिवार्य स्तम्भ | वैकल्पिक स्तम्भ |
|---|---|
| `student_number`, `hold_type` (`unregistered`, `financial`, `academic`, `administrative`, `other`), `reason` | `starts_at` (पूर्वनिर्धारित: आयात गरिएको समय), `ends_at`, `blocks_registration` (पूर्वनिर्धारित 1), `blocks_grades`, `blocks_certificates` |

- हरेक पङ्क्तिले नयाँ रोक बनाउँछ (स्रोत `import`)। एउटै फाइल दुई पटक आयात गर्दा रोकहरू दुई पटक बन्छन्, त्यसैले फेरि आयात गर्नुअघि सूची जाँच्नुहोस्।
- समय `2027-03-15` वा `2027-03-15 09:00` ढाँचामा लेखिन्छ (समय क्षेत्र नभएमा सर्भरको, UTC)। `ends_at` `starts_at` पछि हुनुपर्छ।
- अज्ञात विद्यार्थी नम्बर भएका पङ्क्ति असफल हुन्छन्। रोकहरू स्क्रिनमा कारणसहित हटाइन्छन् ([अध्याय 20](20-registration.md))।

```csv
student_number,hold_type,reason,ends_at
202312345,financial,Tuition unpaid 2027-1,
202254321,academic,Probation meeting needed,2027-03-15
```

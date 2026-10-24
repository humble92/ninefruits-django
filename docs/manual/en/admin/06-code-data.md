# 6. Code data, countries, languages

Menu: **Reference data > Code lists**, **Countries**, **Languages** (`Manage code data, countries and languages` permission)

## Code data

Short lists that differ from one university to another. Each list (type) has code values.

| List code | Purpose | Legacy system (YUSTIC) |
|---|---|---|
| `ethnicity` | Ethnicity | `FNATION` |
| `admission_type` | Admission type | `FADMDIST` |
| `room_type` | Room type | `ROOM.FORWHAT` |

- The system lists (the three above) are looked up by code in the application, so their list codes cannot be changed or deleted. Values can be added freely.
- Open a list and add values under **Codes** below. Codes use lowercase letters, digits and underscores (for example `korean`). Enter the name per language; the English name is required.
- Do not delete values that are no longer used; turn off **Active** instead. A value cannot be deleted while data still uses it.
- Enter many values with [CSV import](09-csv-import.md).

## Countries and languages

The ISO standard lists (249 countries, about 180 languages) are loaded during installation. Names are filled in automatically for the installed languages.

- To change the name shown on screen, change it under **Edit**. The changed name is kept through later system updates.
- To hide an entry from selection lists, turn off **Active**.

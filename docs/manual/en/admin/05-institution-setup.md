# 5. Institution settings and initial setup order

## Institution settings

Set under **Settings > Institution** (`Manage institution settings` permission).

| Setting | Description |
|---|---|
| Institution name | Entered per language. Shown at the top left of the administration panel |
| Time zone | The reference for judging term dates and term windows, for example `Asia/Seoul`. Every stored time is displayed in this time zone |
| Offered languages | Languages users can choose. Only languages with installed translation files appear in the list |
| Default language | Used for users who have not chosen a language and when the browser language is unknown |

## Initial setup order for a new university

After the IT operator has finished `setup_install` (operations manual, [Installation](../operations/installation.md)), the business administrator enters data in the order below. Later steps refer to codes from earlier steps, so keep the order.

1. **Institution settings**: name, time zone, languages (this chapter)
2. **Code data**: ethnicity, admission type and room type values ([chapter 6](06-code-data.md)). If the Korean university profile was applied during installation, room types already exist.
3. Check **Org unit types**, then **Org units**: university → college → department ([chapter 7](07-org-units-and-programs.md)). For many units, use CSV ([chapter 9](09-csv-import.md)).
4. **Programs**: degree programs per department ([chapter 7](07-org-units-and-programs.md))
5. **Buildings**, **Rooms** ([chapter 8](08-facilities.md), CSV possible)
6. Check **Term types** and **Class periods** ([chapter 10](10-terms.md))
7. Check **Course categories** and **Grade scales**. One default scale must be designated ([chapter 11](11-course-categories-and-grade-scales.md))
8. **Academic years** → **Terms** → **Term windows** per term ([chapter 10](10-terms.md))
9. **Users and access**: roles that need an org unit scope, such as department assistants, can now pick the department as the scope target ([chapter 2](02-users-and-roles.md))

When the data is entered, ask the IT operator to check the term windows with `uv run manage.py term_inspect`.

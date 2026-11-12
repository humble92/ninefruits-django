# 6. Nomenclatures, pays, langues

Menu : **Données de référence > Nomenclatures**, **Pays**, **Langues** (autorisation `Gérer les nomenclatures, pays et langues`)

## Nomenclatures

De courtes listes qui diffèrent d’une université à l’autre. Chaque liste (type) comporte des valeurs de code.

| Code de la liste | Usage | Ancien système (YUSTIC) |
|---|---|---|
| `ethnicity` | Ethnie | `FNATION` |
| `admission_type` | Type d’admission | `FADMDIST` |
| `room_type` | Type de salle | `ROOM.FORWHAT` |

- Les listes système (les trois ci-dessus) sont recherchées par leur code dans l’application ; leurs codes de liste ne peuvent donc être ni modifiés ni supprimés. Les valeurs peuvent être ajoutées librement.
- Ouvrez une liste et ajoutez des valeurs sous **Codes** en dessous. Les codes utilisent des lettres minuscules, des chiffres et des tirets bas (par exemple `korean`). Saisissez le nom pour chaque langue ; le nom en anglais est obligatoire.
- Ne supprimez pas les valeurs qui ne sont plus utilisées ; désactivez plutôt **Actif**. Une valeur ne peut pas être supprimée tant que des données l’utilisent.
- Saisissez de nombreuses valeurs avec l’[import CSV](09-csv-import.md).

## Pays et langues

Les listes normalisées ISO (249 pays, environ 180 langues) sont chargées lors de l’installation. Les noms sont renseignés automatiquement pour les langues installées.

- Pour changer le nom affiché à l’écran, modifiez-le sous **Modifier**. Le nom modifié est conservé lors des mises à jour ultérieures du système.
- Pour masquer une entrée dans les listes de sélection, désactivez **Actif**.

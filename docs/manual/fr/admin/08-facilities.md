# 8. Bâtiments et salles

Menu : **Données de référence > Bâtiments**, **Salles** (autorisation `Gérer les bâtiments et les salles`)

## Bâtiments

Saisissez le code (par exemple `SCI`), le nom (pour chaque langue) et l’adresse. Un bâtiment qui comporte des salles ne peut pas être supprimé ; désactivez donc **Actif** lorsqu’il n’est plus utilisé.

## Salles

| Champ | Description |
|---|---|
| Bâtiment, Numéro de salle | Les numéros de salle sont uniques au sein d’un bâtiment, par exemple `101` |
| Nom | Facultatif, par exemple Grand amphithéâtre |
| Type de salle | Une valeur de la nomenclature `room_type` (salle de cours, laboratoire, etc.) |
| Unité organisationnelle | Le département qui gère la salle (facultatif) |
| Capacité | Comparée à la capacité du groupe lors de l’élaboration des emplois du temps ([chapitre 18](18-sections-and-timetables.md)) |
| Utilisée pour les emplois du temps | Lorsque ce champ est désactivé, la salle est écartée lors de l’élaboration des emplois du temps (bureaux, locaux de stockage, etc.) |

S’il y a beaucoup de salles, utilisez l’[import CSV](09-csv-import.md). Les bâtiments doivent être enregistrés au préalable.

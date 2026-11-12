# 7. Unités organisationnelles et formations

Menu : **Données de référence > Types d’unité organisationnelle**, **Unités organisationnelles**, **Formations**

## Unités organisationnelles

Universités, facultés, départements, spécialités et services administratifs sont gérés sur un seul écran. Ils remplacent les facultés (`SFCOLLEGE`) et les départements (`SFDEPARTMENT`) de l’ancien système (YUSTIC).

| Champ | Description |
|---|---|
| Code | Un code d’identification permanent, par exemple `CSE` |
| Type | Université, faculté, département, etc. (d’autres types peuvent être ajoutés sur l’écran Types d’unité organisationnelle) |
| Nom, Nom court | Pour chaque langue |
| Parent | L’unité à laquelle celle-ci appartient. Une unité ne peut pas être déplacée sous elle-même ni sous l’une de ses propres descendantes |
| Valide à partir du, Valide jusqu’au | La période d’existence de l’unité. Une date de fin vide signifie qu’elle fonctionne actuellement |

- La liste affiche par défaut **Uniquement les éléments en vigueur**. Désactivez le filtre pour voir également les unités passées.
- Lorsqu’une unité organisationnelle est choisie comme périmètre d’une attribution de rôle, toutes les unités situées en dessous sont incluses. Exemple : périmètre faculté d’ingénierie = tous les départements de la faculté d’ingénierie.

## Réorganisations

Les dossiers étudiants et les notes passés doivent renvoyer à l’unité telle qu’elle était à l’époque ; une unité n’est donc pas modifiée sur place, le changement est enregistré comme une **réorganisation**.

1. Ouvrez la page **Modifier** de l’unité qui disparaît (ou qui change).
2. Appuyez sur **Réorganiser**.
3. Choisissez le type de changement.
   - **Renommée** : créez d’abord l’unité sous son nouveau nom et désignez-la comme successeur
   - **Fusionnée** : lorsque plusieurs unités fusionnent en une seule, désignez le même successeur depuis chaque unité
   - **Scindée** : lorsqu’une unité est divisée en plusieurs, désignez plusieurs successeurs
   - **Rattachée ailleurs** : lorsque l’unité passe sous un autre parent en tant que nouvelle unité
4. Saisissez la **Date d’effet** et un motif. L’unité prend fin la veille de la date d’effet, et l’enregistrement apparaît dans la liste **Successeurs** en dessous.

Une simple faute de frappe se corrige en **modifiant** le nom, et non par une réorganisation (la modification de données est enregistrée).

## Formations

Formations diplômantes ou formations de spécialité. Les dossiers étudiants appartiennent à une formation ([chapitre 12](12-people-and-student-records.md)).

| Champ | Description |
|---|---|
| Code, Nom, Intitulé du diplôme | Exemple d’intitulé du diplôme : Licence en sciences de l’ingénieur |
| Niveau de diplôme | Diplôme de premier cycle court, Licence, Master, Doctorat, Certificat, Hors diplôme |
| Unité organisationnelle | Le département qui gère la formation |
| Durée normale | Durée normale des études (années) |
| Valide à partir du, Valide jusqu’au | La période d’existence de la formation, et non la période pendant laquelle elle admet de nouveaux étudiants |
| Accepte les doubles majeures, Accepte les mineures | Indique si les étudiants d’autres formations peuvent demander cette formation comme double majeure ou mineure ([chapitre 19](19-second-majors-and-minors.md)) |

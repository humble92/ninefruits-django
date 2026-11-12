# 9. Import CSV

Utilisez le bouton **Importer un CSV** en haut des écrans des unités organisationnelles, des formations, des bâtiments, des salles et des nomenclatures (autorisation `Importer des données de référence depuis un CSV`). Les dossiers étudiants, les enseignants, les cours et les blocages d’inscription s’importent de la même manière (voir ci-dessous). Les fichiers très volumineux peuvent être importés de la même manière par l’exploitant informatique avec la commande `reference_import`.

## Règles communes

- La première ligne contient les noms des colonnes (tableaux ci-dessous). L’encodage est UTF-8 ; dans Excel, enregistrez au format « CSV UTF-8 ».
- Une ligne dont le code existe déjà **met à jour** cet enregistrement. Importer à nouveau le même fichier ne crée pas de doublons.
- Les colonnes par langue prennent la forme `colonne_langue` : `name_en`, `name_ko`, `name_zh-hans`. Les nouvelles lignes exigent le nom en anglais (`name_en`). Les cellules vides n’effacent pas les traductions existantes.
- Les dates s’écrivent `2026-03-01` ; les valeurs oui/non `1`/`0` ou `true`/`false`.
- L’en-tête est vérifié en premier (s’il manque une colonne obligatoire, rien n’est importé). Les fichiers de 500 lignes au plus sont importés immédiatement ; les fichiers plus volumineux sont traités en arrière-plan (Celery). Le résultat s’affiche sur la page de l’import sous **Données de référence > Imports CSV** (lignes importées, lignes en échec et leurs motifs). Si des lignes ont échoué, **Télécharger les lignes en échec** fournit un CSV avec le motif pour chaque ligne. Corrigez-le et importez uniquement ce fichier.
- Les noms de colonnes doivent correspondre aux tableaux ci-dessous ; les colonnes inconnues sont ignorées. Le nom de colonne `name_zh_CN` du système d’origine est accepté comme `name_zh-hans`.

## Formats des colonnes

| Type | Colonnes obligatoires | Colonnes facultatives |
|---|---|---|
| Unités organisationnelles | `code`, `type` (code du type d’unité organisationnelle), `name_en`, `effective_start_date` | `parent` (code du parent), `name_ko` etc., `short_name_*`, `effective_end_date`, `sort_order` |
| Formations | `code`, `org_unit` (code de l’unité organisationnelle), `degree_level`, `name_en`, `effective_start_date` | `degree_title_*`, `standard_duration_years`, `effective_end_date`, `allows_second_major`, `allows_minor` |
| Bâtiments | `code`, `name_en` | `name_*`, `address`, `is_active` |
| Salles | `building` (code du bâtiment), `code` (numéro de salle) | `name_*`, `room_type` (code du type de salle), `org_unit`, `capacity`, `is_schedulable`, `is_active` |
| Valeurs de code | `type` (code de la liste), `code`, `name_en` | `name_*`, `sort_order`, `is_active` |

Valeurs de `degree_level` : `associate`, `bachelor`, `master`, `doctorate`, `certificate`, `non_degree`

Pour les unités organisationnelles, les unités parentes doivent venir en premier (triez dans l’ordre université → faculté → département).

## Exemple : unités organisationnelles

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## Étudiants et enseignants

Les dossiers étudiants sont rapprochés et mis à jour par `student_number`, les enseignants par `employee_number`. Les deux types partagent les colonnes relatives à la personne.

| Type | Colonnes obligatoires pour les nouvelles lignes | Colonnes facultatives |
|---|---|---|
| Dossiers étudiants | `student_number`, `program` (code de la formation), `admission_date`, `family_name` | `catalog_year` (année d’admission si vide), `year_level`, `status`, `graduation_date`, `institutional_email` |
| Enseignants | `employee_number`, `org_unit` (code de l’unité organisationnelle), `employment_type`, `family_name` | `academic_title_*`, `hire_date`, `end_date` |
| Colonnes relatives à la personne (communes) | — | `given_name`, noms par langue tels que `name_ko`, `birth_date`, `gender`, `email`, `phone`, `national_id` |

- Valeurs de `status` : `enrolled`, `on_leave`, `withdrawn`, `dismissed`, `graduated` (`graduation_date` est obligatoire pour `graduated`). Un statut modifié par import est traité comme une **correction de données** et ne crée aucun historique de changement de statut. Les changements réels sont enregistrés à l’écran ([chapitre 13](13-status-changes-and-advisors.md)).
- Valeurs de `employment_type` : `full_time`, `part_time`, `adjunct`, `visiting`, `emeritus`. Valeurs de `gender` : `female`, `male`, `other`, `undisclosed`.
- Si le `national_id` d’un nouveau dossier étudiant correspond à une personne existante, le dossier est rattaché à cette personne (réadmission). Sinon, une nouvelle personne est créée. Lors d’une mise à jour, les cellules vides n’effacent pas les valeurs existantes.
- Les étudiants et enseignants importés n’ont pas de compte. Envoyez-leur une invitation avec les [invitations à créer un compte](14-merge-and-invitations.md#invitations-à-créer-un-compte).

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

L’import des versions de cours est décrit au [chapitre 17](17-courses-and-curriculum.md), celui des blocages d’inscription au [chapitre 20](20-registration.md).

## Blocages d’inscription

**Importer un CSV** en haut de la liste **Inscriptions pédagogiques > Blocages** (autorisation `Poser et lever des blocages, accorder des dérogations aux règles`) ou `uv run manage.py reference_import registration_holds`. Sert à charger les données `SRDENY` de l’ancien système ou la liste des étudiants en défaut de paiement transmise par le service financier.

| Colonnes obligatoires | Colonnes facultatives |
|---|---|
| `student_number`, `hold_type` (`unregistered`, `financial`, `academic`, `administrative`, `other`), `reason` | `starts_at` (par défaut : heure de l’import), `ends_at`, `blocks_registration` (par défaut 1), `blocks_grades`, `blocks_certificates` |

- Chaque ligne crée un nouveau blocage (source `import`). Importer deux fois le même fichier crée les blocages deux fois ; vérifiez donc la liste avant de réimporter.
- Les heures s’écrivent `2027-03-15` ou `2027-03-15 09:00` (sans fuseau horaire, celui du serveur, UTC). `ends_at` doit être postérieur à `starts_at`.
- Les lignes comportant un numéro d’étudiant inconnu échouent. Les blocages sont levés à l’écran avec un motif ([chapitre 20](20-registration.md)).

```csv
student_number,hold_type,reason,ends_at
202312345,financial,Tuition unpaid 2027-1,
202254321,academic,Probation meeting needed,2027-03-15
```

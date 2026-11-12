# 25. Salle de classe de l’enseignant et présences

Menu : les enseignants utilisent **Mes enseignements > Liste et présences** dans le portail (`/portal/sections/{section ID}/attendance/`), les étudiants **Présences** dans le portail (`/portal/attendance/`). Le personnel utilise l’onglet **Séances** de l’écran **Cours et groupes > Groupes > Modifier** dans le panneau d’administration.

| Qui | Ce qu’ils peuvent faire |
|---|---|
| Enseignants affectés | Liste des étudiants (avec photos) et CSV, feuille d’émargement PDF, génération, ajout et annulation de séances, saisie des présences |
| Personnel disposant de `Planifier les groupes (enseignants, horaires, salles)` (dans son périmètre) | Comme les enseignants + séances dans le panneau d’administration |
| Personnel disposant de `Consulter les groupes` (dans son périmètre) | Liste des étudiants, feuille d’émargement, consultation des présences |
| Étudiants | Leurs propres présences |

Les fonctions de salle de classe telles que les annonces, les devoirs et les supports sont laissées au LMS (plan de portage, section 12).

## Différences avec l’ancien système

- **L’ancien système (YUSTIC) n’enregistrait pas les présences.** Sa « feuille d’émargement » était un PDF qui imprimait des cases vides (de 27 à 34, selon la copie) à côté de la liste des étudiants, sans dates ni totaux. Le nouveau système crée des **séances** à partir des horaires, enregistre présent, en retard, absent ou excusé pour chaque séance, et imprime les relevés et les totaux sur la feuille d’émargement PDF.
- **Liste des étudiants.** L’écran enseignant de l’ancien système n’affichait que les numéros d’étudiant et les noms (et exposait le numéro d’enregistrement de résident et l’adresse dans une fenêtre contextuelle) et ne permettait pas de téléchargement Excel. Le nouveau système n’affiche que le numéro d’étudiant, le nom, la photo, la formation, l’année d’études et l’e-mail de contact, et permet le téléchargement en CSV. Les téléchargements sont enregistrés dans le journal d’audit.
- **Accès des enseignants à leurs étudiants.** Une politique de sécurité au niveau des lignes (`student_records_instructor_select`, fonction `util.taught_student_record_ids()`) permet aux enseignants de voir les dossiers étudiants et les personnes des étudiants de leurs groupes, et les règles de visibilité de l’application y correspondent (auparavant, l’original n’affichait que leurs étudiants suivis, ce qui laissait les noms vides même sur l’écran de saisie des notes).

## Séances

- **Générer** : une séance pour chaque occurrence des horaires hebdomadaires (jour, heure, créneau). Les enseignants utilisent le bouton **Générer à partir des horaires** ; le personnel utilise le bouton **Générer les séances** au-dessus de l’onglet **Séances** (avec une page de confirmation) ou la commande `uv run manage.py attendance_generate_sessions {term}` (semestre entier). Les séances et présences existantes ne sont pas modifiées ; la génération peut donc être relancée après une modification des horaires. Les groupes annulés sont ignorés.
- **Ajouter une séance** : un cours en dehors des horaires, comme un cours de rattrapage (date, début, fin). Uniquement à des dates comprises dans la session, et une seule séance par date et heure de début.
- **Annuler** : annule la séance avec un motif. La séance est conservée mais exclue des totaux. **Rétablir** la réactive.
- Il n’y a pas de calendrier des jours fériés. Annulez les séances tombant un jour férié (une fois un calendrier des semestres ajouté, le générateur pourra les omettre).

## Saisie des présences

Sous **Présences** de la séance, choisissez présent, en retard, absent ou excusé pour chaque étudiant ajoutez une remarque (200 caractères) puis **Enregistrer les présences**. Le plus rapide est d’utiliser **Tous présents** (marque tout le monde présent sans enregistrer) puis de modifier les exceptions.

- Les présences peuvent être saisies à partir du jour de la séance (pas pour les séances futures ou annulées).
- Un nouvel enregistrement n’enregistre que les étudiants modifiés, et l’événement d’audit (`attendance.recorded`) conserve l’ancienne et la nouvelle valeur pour chaque étudiant.
- Effacer le statut remet l’étudiant à l’état « non saisie ».
- Seuls les étudiants inscrits et ayant terminé peuvent être enregistrés (les étudiants désinscrits ou ayant abandonné ne figurent pas sur la liste).

## Totaux

| Élément | Définition |
|---|---|
| Séances tenues | Séances non annulées dont la date est antérieure ou égale à aujourd’hui |
| Taux de présence | (présent + en retard + excusé) ÷ séances tenues × 100, une décimale (demi arrondi au supérieur) |
| Non saisie | Séances tenues sans enregistrement |

Il n’existe pas de règle convertissant un nombre de retards en absence ni attribuant un F au-delà d’un tiers d’absences. Cela diffère d’une université à l’autre ; les enseignants tiennent donc compte eux-mêmes des présences dans la note. Les règles de décompte se trouvent dans un seul service (`AttendanceSummary`) : la liste des étudiants, la feuille d’émargement et la page de l’étudiant affichent donc les mêmes nombres.

## Feuille d’émargement PDF et liste des étudiants CSV

Les deux téléchargements sont enregistrés dans le journal d’audit (`attendance.sheet_exported`, `attendance.roster_exported`). Les valeurs CSV commençant par `=`, `+`, `-` ou `@` (ou par une tabulation ou un saut de ligne) sont exportées précédées d’une apostrophe simple afin de ne pas être exécutées comme des formules.

- **Feuille d’émargement (PDF)** (`/sections/{section ID}/attendance-sheet`) : A4 paysage. Les étudiants en lignes, les séances en colonnes (séances annulées exclues), marques O/△/X/E et totaux par étudiant. Les séances à venir restent vides, la feuille sert donc aussi à la saisie manuscrite. Lorsque le serveur PDF (Gotenberg) ne répond pas, « Le PDF n’a pas pu être créé » s’affiche.
- **Liste des étudiants (CSV)** (`/sections/{section ID}/roster.csv`) : numéro d’étudiant, nom, formation, année d’études, e-mail de contact, statut d’inscription. UTF-8 avec BOM, il s’ouvre donc directement dans Excel.

## Portail étudiant

**Présences** : par semestre (par défaut le dernier semestre commencé) et par cours, le nombre de présences, de retards, d’absences et d’absences excusées et le taux de présence ; en dépliant, le relevé par séance tenue (uniquement ce que l’enseignant a saisi, sinon « Non saisie »).

## Procédure d’exploitation

1. Avant le début du semestre, arrêtez les horaires des groupes ([chapitre 18](18-sections-and-timetables.md)).
2. Créez les séances avec `uv run manage.py attendance_generate_sessions {term} --actor=...` (les enseignants peuvent aussi les créer à l’écran). Un seul groupe : `--section=CSE2010-01` ; uniquement le nombre de groupes : `--dry-run` ([commandes d’exploitation](../operations/commands.md)).
3. Relancez la commande lorsque les horaires changent. Les séances des horaires supprimés ne sont pas supprimées automatiquement ; annulez-les.

## Écrans de cette installation

Les écrans et les fonctions sont ceux de l’original (Filament, Livewire) ; certaines commandes fonctionnent un peu différemment.

- Onglet **Séances** de l’écran de modification du groupe dans le panneau d’administration : date, heure, salle, statut, enregistrements saisis, motif. **Annuler** sur une ligne ouvre une page pour le motif, **Rétablir** une page de confirmation. **Générer les séances** est un bouton d’action en haut de l’écran. Le personnel ne disposant que de `Consulter les groupes` voit l’onglet sans les boutons.
- Dans le portail enseignant, **Annuler** ouvre un champ de motif dans la ligne de la séance ; saisissez le motif et appuyez de nouveau sur **Annuler** (au lieu de la boîte de dialogue du navigateur de l’original).
- La page de saisie des **Présences** se termine par `?meeting={meeting ID}` et peut donc être mise en favori. **Retour** revient à la liste des étudiants et à la liste des séances.
- Avec la sécurité au niveau des lignes, la liste des étudiants n’est remplie que pour les personnes qui peuvent voir les inscriptions et les dossiers étudiants. Les rôles par défaut (Affaires pédagogiques, Gestionnaire de département) disposent aussi de `Consulter les inscriptions et les listes d’étudiants` et de `Consulter les dossiers étudiants`. Un rôle n’ayant que `Planifier les groupes (enseignants, horaires, salles)` voit une liste et une feuille vides (comme dans l’original).

[Sommaire du manuel d’administration](README.md)

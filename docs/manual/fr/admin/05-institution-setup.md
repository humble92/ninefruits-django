# 5. Paramètres de l’établissement et ordre de configuration initiale

## Paramètres de l’établissement

À définir sous **Paramètres > Établissement** (autorisation `Gérer les paramètres de l’établissement`).

| Paramètre | Description |
|---|---|
| Nom de l’établissement | Saisi pour chaque langue. Affiché en haut à gauche du panneau d’administration |
| Fuseau horaire | La référence pour apprécier les dates des semestres et des périodes de gestion, par exemple `Asia/Seoul`. Toutes les heures enregistrées sont affichées dans ce fuseau horaire |
| Langues proposées | Les langues que les utilisateurs peuvent choisir. Seules les langues dont les fichiers de traduction sont installés apparaissent dans la liste |
| Langue par défaut | Utilisée pour les utilisateurs qui n’ont pas choisi de langue et lorsque la langue du navigateur est inconnue |

## Ordre de configuration initiale pour une nouvelle université

Une fois que l’exploitant informatique a terminé `setup_install` (manuel d’exploitation, [Installation](../operations/installation.md)), l’administrateur métier saisit les données dans l’ordre ci-dessous. Les étapes ultérieures font référence aux codes des étapes précédentes : respectez donc cet ordre.

1. **Paramètres de l’établissement** : nom, fuseau horaire, langues (ce chapitre)
2. **Nomenclatures** : valeurs d’ethnie, de type d’admission et de type de salle ([chapitre 6](06-code-data.md)). Si le profil université coréenne a été appliqué lors de l’installation, les types de salle existent déjà.
3. Vérifiez les **Types d’unité organisationnelle**, puis les **Unités organisationnelles** : université → faculté → département ([chapitre 7](07-org-units-and-programs.md)). S’il y a beaucoup d’unités, utilisez le CSV ([chapitre 9](09-csv-import.md)).
4. **Formations** : formations diplômantes par département ([chapitre 7](07-org-units-and-programs.md))
5. **Bâtiments**, **Salles** ([chapitre 8](08-facilities.md), CSV possible)
6. Vérifiez les **Types de semestre** et les **Créneaux horaires** ([chapitre 10](10-terms.md))
7. Vérifiez les **Catégories de cours** et les **Barèmes de notation**. Un barème par défaut doit être désigné ([chapitre 11](11-course-categories-and-grade-scales.md))
8. **Années universitaires** → **Semestres** → **Périodes de gestion** de chaque semestre ([chapitre 10](10-terms.md))
9. **Utilisateurs et accès** : les rôles qui nécessitent un périmètre d’unité organisationnelle, comme les gestionnaires de département, peuvent désormais choisir le département comme cible du périmètre ([chapitre 2](02-users-and-roles.md))

Une fois les données saisies, demandez à l’exploitant informatique de vérifier les périodes de gestion avec `uv run manage.py term_inspect`.

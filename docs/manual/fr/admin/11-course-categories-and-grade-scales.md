# 11. Catégories de cours et barèmes de notation

## Catégories de cours

Menu : **Données de référence > Catégories de cours** (autorisation `Gérer les catégories de cours`). Remplace `SFOBJDIST` de l’ancien système (YUSTIC).

La classification des cours, par exemple culture générale obligatoire ou option de spécialité. Les catégories peuvent être regroupées en définissant un **Parent** (par exemple Culture générale → Culture générale obligatoire, Culture générale optionnelle). Les conditions d’obtention du diplôme ([chapitre 17](17-courses-and-curriculum.md), [chapitre 26](26-graduation.md)) y font référence, comme dans « 30 crédits de cours obligatoires de spécialité ».

## Barèmes de notation

Menu : **Données de référence > Barèmes de notation** (autorisation `Gérer les barèmes de notation`). Remplace `SSCOREDEF` de l’ancien système.

| Champ du barème | Description |
|---|---|
| Points maximum | Par exemple 4.5 |
| Par défaut | Un seul barème peut être le barème par défaut. Cette option ne peut être activée que tant qu’aucun barème n’est le barème par défaut (voir ci-dessous) |

Ouvrez un barème et ajoutez des notes sous **Notes** en dessous.

| Champ de la note | Description |
|---|---|
| Note | Par exemple `A+`, `P` |
| Points | Obligatoires pour les notes qui comptent dans la moyenne |
| De/À (%) | Tranches de conversion des scores bruts (facultatif), par exemple A+ 95–100 |
| Compte dans la moyenne | Désactivez-le pour les notes exclues de la moyenne, comme P/NP |
| Admis | Désactivez-le pour les notes qui ne donnent pas de crédits, comme F ou NP |
| Pour | Cours notés (notes littérales), Cours réussi/échoué (P, NP) ou Les deux (par exemple I, incomplet). L’écran de saisie des notes n’affiche que les notes correspondant au mode de notation du cours |

**Le barème par défaut est fixé à l’installation et ne peut pas être modifié** (décision du 2026-10-23), car toutes les notes et moyennes sont exprimées dans ce barème. Définissez-le avec `setup_install --grade-scale=4.5|4.3` ; sans cette option, le barème du premier profil devient le barème par défaut. L’indicateur par défaut ne peut pas être modifié à l’écran et le barème par défaut ne peut pas être supprimé. Les tranches de scores et les points de chaque note se modifient sur cet écran ([chapitre 21](21-grades.md)).

Barèmes chargés par les profils

- Université coréenne : barème sur 4.5 (`KR45`) : A+ 4.5 (95–100), A0 4.0 (90–), B+ 3.5 (85–), B0 3.0 (80–), C+ 2.5 (75–), C0 2.0 (70–), D+ 1.5 (65–), D0 1.0 (60–), F 0, P, NP
- `--grade-scale=4.3` ou l’ancien profil YUST : barème sur 4.3 (`KR43` ou `YUST43`) : A+ 4.3 (97–100), A0 4.0 (93–), A- 3.7 (90–), B+ 3.3 (87–), B0 3.0 (83–), B- 2.7 (80–), C+ 2.3 (77–), C0 2.0 (73–), C- 1.7 (70–), D+ 1.3 (67–), D0 1.0 (63–), D- 0.7 (60–), F 0, P, NP (l’ancien profil comprend aussi N et I). Les tranches de scores commencent par intervalles de 3 points ; ajustez-les donc aux règles de l’établissement.

Un barème déjà utilisé dans des notes ne peut pas être supprimé.

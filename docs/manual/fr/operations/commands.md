# Référence des commandes de gestion

- Public : exploitants informatiques
- Périmètre : toutes les commandes enregistrées par les applications Ninefruits de ce dépôt (`ninefruits/*/management/commands/`) et les commandes intégrées de Django utilisées en exploitation. Lorsqu’une commande est ajoutée, une entrée `### \`command\`` doit aussi être ajoutée à ce document (dans les 16 langues), sinon la CI échoue (`tests/tooling/test_command_documentation.py`).

## Conventions communes

Toutes les commandes s’exécutent avec `uv run manage.py {command}`. Dans l’environnement de développement Docker : `docker compose exec app uv run manage.py {command}`.

| Élément | Règle |
|---|---|
| Nom | Le `{context}:{action}` de l’original devient `{context}_{action}` (les noms de commandes Django ne peuvent pas contenir `:`). Exemple : `term:close` → `term_close` |
| Enregistrement d’audit | Les commandes qui modifient des données (« Audit : enregistré » ci-dessous) écrivent à chaque exécution la commande, les arguments, les options, l’utilisateur du système d’exploitation, le code de sortie et le résultat dans le journal d’activité (journal `command`). Consultez-les dans **Audit > Journal d’activité** du panneau d’administration |
| Identifiant d’exécution | Chaque exécution reçoit un identifiant commençant par `cmd-` à la place de l’identifiant de requête. Le journal d’activité, les modifications de données effectuées par cette exécution et les tâches Celery qu’elle a lancées portent toutes le même identifiant : la question « quelle commande a fait cette modification ? » se résout donc par l’identifiant. `--actor` est une valeur fournie par l’exploitant ; elle n’est donc pas reportée dans la colonne utilisateur des modifications de données (l’acteur réel est l’utilisateur du système d’exploitation) |
| `--actor=<email>` | Commun à toutes les commandes auditées. Enregistre le compte de l’administrateur responsable. Une adresse e-mail inconnue interrompt l’exécution |
| `--dry-run` | Affiche le résultat sans rien modifier. Disponible pour les opérations difficiles à annuler |
| `--force` | S’exécute sans demande de confirmation (pour les planifications et les scripts de déploiement) |
| `--reason=` | Disponible pour les commandes qui exigent un motif |
| Codes de sortie | 0 succès, 1 échec ou annulation, 2 une commande de contrôle a détecté un problème |
| Contexte de base de données | Pendant l’exécution de la commande, l’acteur de la session de base de données est défini à `system:command:{command}` et apparaît dans les modifications de données (déclencheur) |

## Commandes intégrées de Django

### `migrate`

- Objet : applique les migrations de la base de données. Une surcouche Ninefruits de la commande Django : sans `--database`, elle utilise la connexion du propriétaire du schéma (`migrator`, rôle `app_migrator`). La connexion applicative (`app_runtime`) n’a aucun privilège DDL. `showmigrations` et `sqlmigrate` utilisent aussi par défaut la connexion `migrator`.
- Quand : à la première installation et à chaque déploiement (`setup_install` l’exécute également).
- Options : les mêmes que `migrate` de Django (`app_label`, `migration_name`, `--plan`, `--check`, `--database`).
- Audit : non enregistré (les changements de schéma sont conservés dans l’historique des migrations `django_migrations`)
- Exemples

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- En cas d’échec : pour les erreurs de permission, vérifiez la préparation des rôles de base de données (`db/sql/roles/`) dans le [manuel d’installation](installation.md).

### `collectstatic`

- Objet : rassemble le résultat du build Vite (`static/dist/`) et les fichiers statiques de Django et d’unfold dans `STATIC_ROOT` (`staticfiles/`). Le serveur web (Nginx) sert ce répertoire.
- Quand : à chaque déploiement, après `npm ci && npm run build`.
- Options : `--noinput` (sans questions), `--clear` (supprime les fichiers existants avant la collecte).
- Audit : non enregistré
- Exemples

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- Objet : compile les fichiers de traduction (`.po`) en fichiers `.mo` utilisés à l’exécution. Les fichiers `.mo` ne sont pas conservés dans le dépôt : exécutez donc cette commande à chaque installation et à chaque déploiement. `gettext` doit être installé sur le système.
- Quand : à chaque déploiement et après la modification des fichiers de traduction.
- Options : `--locale=` (par ex. `ko`, `zh_Hans`, `lo`), `--ignore=.venv`.
- Audit : non enregistré
- Exemples

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- Objet : **non utilisée.** Un superutilisateur Django contourne le catalogue des rôles et des autorisations ainsi que la piste d’audit : cette commande se termine donc par une erreur (code de sortie 1) et renvoie vers `security_create_administrator`.
- À la place : créez le premier administrateur avec `security_create_administrator` (comprend l’attribution du rôle d’administrateur système et un enregistrement d’audit).
- Audit : sans objet

## Installation et démonstration (phase 1)

### `setup_install`

- Objet : nouvelles installations et mises à jour. Exécute successivement les migrations, les données essentielles (modèles de rôles et synchronisation des autorisations, pays, langues, types de nomenclatures, types d’unités organisationnelles), les paramètres de l’établissement, le barème de notation, les profils d’installation et le premier administrateur. Peut être relancée sans risque (les données existantes et les valeurs modifiées par les administrateurs sont conservées).
- Quand : à la première installation et à chaque déploiement.
- Options : `--institution-name=`, `--locale=` (langue par défaut), `--timezone=` (par ex. `Asia/Seoul`), `--profile=` (clé du profil d’installation, répétable : `korean-university`, `yust-legacy`), `--grade-scale=` (barème de notation `4.5` ou `4.3` ; figé une fois défini ; vide signifie le barème du premier profil), `--admin-email=`, `--admin-name=`, `--force` (sans questions ; le mot de passe de l’administrateur est lu sur l’entrée standard).
- Audit : enregistré (profils appliqués, création ou non d’un administrateur)
- Exemples

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="Demo University" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="Administrator"
  ```

- Lecture de la sortie : `DONE` pour chaque étape. `Administrator exists` signifie qu’une attribution d’administrateur système existe déjà ; la création a donc été ignorée.
- En cas d’échec : une erreur de clé manquante signifie que `DJANGO_SECRET_KEY` et les valeurs de `pii_generate_key` doivent être définies dans l’environnement. Un échec de migration : vérifiez les rôles de base de données ([installation](installation.md)). `The grade scale is fixed` signifie que `--grade-scale` diffère du barème déjà figé.

### `setup_demo`

- Objet : crée une université fictive (unités organisationnelles, formations, bâtiments et salles, le semestre précédent, le semestre en cours et le suivant autour de la date du jour avec leurs périodes, le profil université coréenne). Affiche les comptes de démonstration fixes par rôle (`registrar@demo.test`, etc., mot de passe `demo-password`). Les volumes sont créés par insertions en masse.
- Quand : environnements de développement, de formation et de démonstration. **Elle ne s’exécute jamais en production (`DJANGO_ENV=production`), même avec `--force`.**
- Options : `--size=tiny|small|medium|large` (environ 20/100/2 000/20 000 étudiants ; `tiny` pour les tests et les vérifications rapides), `--seed=` (même valeur, mêmes données), `--force` (sans confirmation).
- `--student-accounts` : donne un compte à chaque étudiant inscrit et écrit `load-accounts.csv` (e-mail, mot de passe) dans le stockage privé, pour les tests de charge ([test de charge](load-testing.md)).
- Audit : enregistré (taille, graine, durée)
- Exemple : `uv run manage.py setup_demo --size=small --seed=42 --force`
- En cas d’échec : sans données essentielles, les comptes de démonstration sont ignorés (leurs rôles manquent) ; exécutez d’abord `setup_install`. Une nouvelle exécution sur la même base ignore les données de démonstration existantes.

## Données de référence et semestres (phase 1)

### `reference_import`

- Objet : importe des données de référence depuis un CSV, avec les mêmes règles que **Importer un CSV** dans le panneau d’administration (les lignes sont retrouvées par code et mises à jour, les cellules de traduction vides conservent les valeurs existantes, les lignes en échec sont conservées à part).
- Arguments : `type` `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`, `students` (dossiers étudiants), `instructors`, `courses` (versions de cours), `registration_holds` (blocages d’inscription) / `file` CSV UTF-8 avec ligne d’en-tête.
- Options : `--actor=` (obligatoire ; l’import est enregistré sous ce compte et son résultat apparaît sur l’écran **Imports CSV** de ce compte), `--chunk=100` (lignes par tâche Celery), `--dry-run` (contrôle de l’en-tête et nombre de lignes uniquement).
- Audit : enregistré (type, nom du fichier, lignes, numéro d’import, lignes en échec)
- Format des colonnes : [manuel d’administration, chapitre 9](../admin/09-csv-import.md).
- Codes de sortie : lorsque les tâches s’exécutent immédiatement (workers en mode eager), le résultat est affiché et des lignes en échec donnent 2. Lorsque l’import est seulement mis en file, 0. Le résultat et le CSV des lignes en échec se trouvent sous **Données de référence > Imports CSV** dans le panneau d’administration.
- Exemple : `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- Objet : affiche, à un instant donné, les semestres en cours et les périodes de gestion ouvertes (type, semestre, session, nom, critères de public, heure de clôture). Sert à vérifier les paramètres des semestres et des périodes, ou à répondre à des questions telles que « pourquoi l’inscription n’est-elle pas ouverte ? ».
- Options : `--at=` (par défaut maintenant ; par ex. `"2027-02-15 09:00"` ; sans fuseau horaire, celui du serveur (UTC) s’applique ; `"2027-02-15 09:00 Asia/Seoul"` ou `2027-02-15T09:00+09:00` en précisent un).
- Audit : non enregistré (lecture seule)
- Lecture de la sortie : les dates sont évaluées dans le fuseau horaire de l’établissement. Les périodes des semestres planifiés ou archivés ne s’ouvrent jamais. Les heures de clôture sont affichées dans le fuseau horaire de l’établissement.

## Sécurité (phases 0, 2)

### `security_create_administrator`

- Objet : crée un compte doté du rôle d’administrateur système. Généralement appelée par `setup_install`.
- Options : `--email=`, `--name=`, `--password-stdin` (mot de passe lu sur l’entrée standard ; obligatoire pour une exécution non interactive).
- Audit : enregistré (ID de l’utilisateur créé)
- Exemple : `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator"`
- Exemple (non interactif) : `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator" --password-stdin`
- En cas d’échec : `system_administrator role is missing` signifie qu’il faut d’abord exécuter `setup_install`. Le mot de passe doit comporter au moins 12 caractères.

### `security_sync_permissions`

- Objet : aligne la liste des autorisations de la base de données sur le catalogue d’autorisations du code. Les nouvelles autorisations sont créées ; celles absentes du catalogue sont supprimées (et retirées de tous les rôles). Les rôles système reçoivent toujours toutes les autorisations.
- Quand : après un déploiement (`setup_install` le fait dans l’étape des données essentielles).
- Options : `--dry-run` (affiche uniquement la liste des créations et suppressions), `--force` (ignore la confirmation de suppression).
- Audit : enregistré (autorisations créées et supprimées)
- Lecture de la sortie : lignes `create` et `delete`. Une demande de confirmation apparaît en cas de suppressions.
- En cas d’échec : répondre « non » à la confirmation termine avec le code 1 sans rien modifier.

### `security_reencrypt_secrets`

- Objet : après une rotation de `DJANGO_SECRET_KEY`, chiffre à nouveau avec la nouvelle clé les secrets protégés par une clé qui en est dérivée (secrets TOTP des applications d’authentification, graines des codes de récupération, secrets client SSO). Jusque-là, ils sont lus avec la clé précédente placée dans `DJANGO_SECRET_KEY_FALLBACKS`. Exécutez-la avant de retirer la clé précédente ([gestion des clés](security-keys.md)).
- Arguments/options : `--dry-run` (compte uniquement les secrets encore chiffrés avec une clé précédente).
- Audit : enregistré (nombres)
- Lecture de la sortie : `Dry run: 0 authenticator(s) and 0 SSO client secret(s) use a previous key.` signifie que la clé précédente peut être retirée. `cannot be decrypted` signifie qu’une valeur ne peut être lue avec aucune des clés configurées : placez la clé précédente dans `DJANGO_SECRET_KEY_FALLBACKS` et relancez.
- Exemple : `uv run manage.py security_reencrypt_secrets --dry-run`

### `security_reset_mfa`

- Objet : réinitialise la double authentification d’un utilisateur (application d’authentification, codes par e-mail, codes de récupération, appareils mémorisés). L’utilisateur s’enrôle à nouveau à sa connexion suivante. À utiliser lorsque aucun administrateur ne peut se connecter au panneau d’administration (par exemple, le seul administrateur a perdu son téléphone). Sinon, utilisez **Utilisateurs > Réinitialiser la double authentification** dans le panneau d’administration.
- Arguments/options : `{user}` e-mail de l’utilisateur, `--reason=` (obligatoire), `--actor=` (obligatoire ; l’administrateur qui a décidé de la réinitialisation).
- Audit : enregistré (dans le journal d’activité et dans le journal de sécurité, avec le motif)
- Exemple : `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="Phone lost, identity verified by phone call" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- Objet : déverrouille, avant la fin de la période de verrouillage, un compte verrouillé à la suite de mots de passe erronés répétés. Identique à **Utilisateurs > Débloquer la connexion** dans le panneau d’administration.
- Arguments/options : `{user}` e-mail de l’utilisateur, `--reason=` (obligatoire).
- Audit : enregistré (également dans le journal de sécurité)
- Lecture de la sortie : `The account is not locked.` signifie que rien n’a été modifié.
- Remarque : les seuils de verrouillage (tentatives échouées, durée du verrouillage) se définissent sous **Paramètres > Méthodes de connexion** dans le panneau d’administration.

## Personnes et dossiers étudiants (phase 2)

### `people_find_duplicates`

- Objet : liste les personnes qui semblent être une même personne. Les critères sont un numéro d’identification national identique (empreinte de recherche), ou un nom romanisé et une date de naissance identiques. Les personnes fusionnées sont exclues.
- Options : `--limit=100` (nombre de groupes à afficher).
- Audit : non enregistré (lecture seule)
- Codes de sortie : 2 lorsque des doublons potentiels existent.
- Suite à donner : examinez chaque groupe sous **Personnes** dans le panneau d’administration et, s’il s’agit de la même personne, lancez **Fusionner un doublon** depuis la page de la personne à conserver. Une fusion ne peut pas être annulée ([manuel d’administration, chapitre 14](../admin/14-merge-and-invitations.md)).
- Exemple : `uv run manage.py people_find_duplicates --limit=50`

## Admissions (phase 3)

### `admission_matriculate`

- Objet : crée les dossiers étudiants (nouveaux numéros d’étudiant) des candidats ayant confirmé leur inscription dans une campagne d’admission. Identique à l’action groupée **Créer le dossier étudiant** sous **Admissions > Candidatures** dans le panneau d’administration (`MatriculateApplicant`). Chaque candidat est traité séparément : un échec n’arrête donc pas les autres.
- Arguments/options : `cycle` code de la campagne d’admission, `--term=` (obligatoire ; code du semestre d’admission, par ex. `2027-SP` ; la date d’admission est le premier jour du semestre), `--actor=` (obligatoire ; un compte disposant de `Créer les dossiers étudiants des candidats admis` ; seuls les candidats du périmètre de ce compte sont traités), `--dry-run` (liste uniquement).
- Audit : enregistré (campagne, semestre, candidats, créés, numéros de candidature en échec). Chaque candidat reçoit aussi une entrée d’audit métier (`application.matriculated`).
- Codes de sortie : 1 lorsque le code de la campagne ou du semestre est inconnu ou que `--actor` manque, 2 lorsqu’un candidat a échoué.
- Exemple : `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- En cas d’échec : `Only accepted offers without a student record ...` signifie que le candidat a déjà un dossier ou n’a pas confirmé ; `The program is not in effect on the admission date.` signifie que la formation n’est pas en vigueur à la date d’admission (vérifiez la validité de la formation sous Données de référence > Formations) ; `not in your scope` signifie que la candidature est hors du périmètre du compte `--actor`.

### `admission_expire_drafts`

- Objet : marque comme **Expirée** les candidatures en brouillon des campagnes closes et les brouillons non modifiés pendant la durée configurée (**Paramètres > Admissions > Faire expirer les brouillons inactifs après (jours)**, 90 par défaut). Les candidatures expirées n’empêchent plus une nouvelle candidature à la même campagne.
- Quand : planifiée tous les jours à 03:10 (la tâche Celery beat `admission.expire_drafts` exécute cette commande).
- Options : `--dry-run` (comptage uniquement).
- Audit : enregistré (nombre de candidatures expirées)
- Exemple : `uv run manage.py admission_expire_drafts --dry-run`

## Groupes (phase 4)

### `section_copy`

- Objet : démarre la planification d’un nouveau semestre à partir des groupes d’un semestre antérieur. Identique à **Groupes > Copier depuis un autre semestre** dans le panneau d’administration (`CopySections`). Copie à l’état de brouillon les groupes non annulés, avec les enseignants (s’ils sont toujours en poste), les horaires et les salles, les places réservées (heures de libération décalées de l’écart entre les dates de début des semestres) et le syllabus (sous forme de brouillon non publié). La version du cours est remplacée par celle en vigueur au début de la nouvelle session.
- Arguments/options : `from-term`, `to-term` codes de semestre (par exemple `2026-FA`), `--org-unit=` (uniquement les groupes de ce code d’unité organisationnelle ; répétable), `--dry-run` (effectue la copie dans une transaction puis l’annule : le rapport est donc exact), `--actor=` (obligatoire ; seuls les groupes compris dans le périmètre de l’autorisation `Planifier les groupes (enseignants, horaires, salles)` de ce compte sont copiés).
- Audit : enregistré (semestres source et cible, nombres de groupes copiés, ignorés et à vérifier ; une copie réelle enregistre aussi l’événement d’audit métier `sections.copied`)
- Lecture de la sortie : `skipped` signifie que le semestre cible possède déjà le même code de groupe ou qu’aucune version de cours n’est en vigueur ; `note` signifie que le groupe a été copié mais que quelque chose a été omis (copié sans salle parce que la salle est déjà occupée, enseignant parti à la retraite, etc.). Les sessions sont mises en correspondance par code ; à défaut, le groupe va dans la session semestre complet.
- Codes de sortie : 1 pour un code de semestre inconnu ou un `--actor` manquant.
- Exemple : `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- Objet : contrôle les groupes d’un semestre avant la publication de l’emploi du temps. La double réservation des salles et des enseignants est déjà empêchée par la base de données ; cette commande repère les problèmes que la base de données autorise : capacité supérieure à celle de la salle, version de cours non en vigueur à la date de début de la session, enseignant parti à la retraite, places réservées au-delà de la capacité, dates de séances hors de la session. Elle contrôle aussi les conflits de salles dans des données arrivées sans contraintes, comme une restauration de sauvegarde.
- Arguments : `term` code du semestre.
- Audit : non enregistré (lecture seule)
- Codes de sortie : 2 en présence de problèmes, 1 pour un code de semestre inconnu. Les groupes qui n’ont pas encore d’enseignant, de salle ou d’horaire sont affichés à titre d’information uniquement (`Note`).
- Exemple : `uv run manage.py schedule_check_conflicts 2027-SP`

## Inscription pédagogique (phase 5)

### `registration_preflight`

- Objet : contrôle un semestre avant l’ouverture des inscriptions. Affiche les périodes d’inscription et d’ajout/retrait, l’ensemble de règles, le nombre de groupes publiés, les groupes de capacité 0, les places réservées au-delà de la capacité, les versions de cours non en vigueur à la date de début de la session, le nombre d’étudiants actifs non couverts par un plafond de crédits et le nombre d’étudiants faisant l’objet d’un blocage d’inscription.
- Arguments : `term` code du semestre (par exemple `2027-SP`).
- Audit : non enregistré (lecture seule)
- Codes de sortie : 2 en présence de problèmes. L’absence d’ensemble de règles est signalée à titre d’information, non comme un problème (les valeurs par défaut des règles s’appliquent).
- Exemple : `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- Objet : montre, règle par règle, ce qui se passerait si l’étudiant s’inscrivait maintenant au groupe (ou à un instant donné). Rien n’est enregistré et aucune tentative n’est consignée. À utiliser pour les questions du type « pourquoi ne puis-je pas m’inscrire ? ».
- Arguments : `student-number` numéro d’étudiant, `section` `code du cours-code du groupe` (par exemple `CSE2010-01`).
- Options : `--term=` (code du semestre ; par défaut, le semestre le plus récent comportant ce groupe), `--at=` (instant de l’évaluation ; par exemple `"2027-02-10 10:00 Asia/Seoul"`).
- Audit : non enregistré (lecture seule)
- Lecture de la sortie : pour chaque règle, réussite/échec, blocage/avertissement et le message. Une règle couverte par une dérogation apparaît en échec mais ne bloque pas. La capacité est affichée à part, sous le tableau des règles.
- Codes de sortie : 2 lorsque l’inscription serait refusée.
- Exemple : `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- Objet : inscrit dans l’ordre les étudiants en liste d’attente des groupes qui ont des places libres. Toutes les règles sont revérifiées lors de l’attribution ; les inscriptions en liste d’attente qui échouent à une règle sont retirées de la liste d’attente (avec enregistrement du motif). Les listes d’attente des groupes dont les périodes d’inscription et d’ajout/retrait sont toutes deux closes expirent. Les étudiants reçoivent le résultat par e-mail.
- Arguments/options : `term?` code du semestre (par défaut : tous les semestres ayant des inscriptions en liste d’attente), `--actor=`.
- Audit : enregistré (nombres de groupes, d’attributions, de retraits et d’expirations)
- Quand : lors d’une désinscription, d’un abandon ou d’une libération de places réservées, le groupe concerné est traité immédiatement par une tâche de file d’attente. Cette commande est le filet de sécurité planifié toutes les heures, qui traite ce qui aurait été manqué.
- Exemple : `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- Objet : marque comme traitées les places réservées dont l’heure de libération est passée (par exemple les places réservées aux étudiants de la majeure) et met en file la tâche d’attribution depuis la liste d’attente pour ces groupes. Les places réservées deviennent des places libres dans le calcul dès que l’heure de libération est passée : cette commande ne fait donc que remettre les places à la liste d’attente.
- Audit : non enregistré (s’exécute toutes les 5 minutes ; les résultats des attributions figurent dans les enregistrements d’inscription)
- Quand : planifiée (toutes les 5 minutes, tâche Celery beat `registration.release_reserved_seats`). La tâche d’attribution est `registration.promote_waitlist` par groupe (une à la fois par groupe grâce à un verrou Redis).
- Exemple : `uv run manage.py registration_release_reserved_seats`

## Notes (phase 6)

### `term_close`

- Objet : clôture un semestre. Toutes les notes du semestre doivent être définitives. Pour chaque tranche d’étudiants (100), elle calcule le bilan semestriel (crédits, moyenne du semestre et moyenne cumulée) et détermine la situation académique (situation normale, avertissement académique, examen pour exclusion) et l’éligibilité au tableau d’honneur (les tâches `grading.close_term_records` d’un chord Celery) ; la tâche de finalisation `grading.finish_term_close` classe ensuite le tableau d’honneur par formation, clôt les bilans semestriels en tant qu’enregistrements officiels et fait passer le semestre à l’état **Notes clôturées**. L’avancement est conservé dans `job_batches` et affiché au-dessus de la liste **Notes > Bilans semestriels**. À la fin, le membre du personnel qui l’a lancée reçoit un e-mail. Identique à **Notes > Bilans semestriels > Clôturer le semestre** dans le panneau d’administration.
- Arguments/options : `term` code du semestre, `--dry-run` (vérifie seulement si le semestre peut être clôturé), `--reason=` (motif conservé dans l’enregistrement), `--actor=`.
- Audit : enregistré (nombre d’étudiants, nombre de groupes ayant des notes non définitives, identifiant du lot). À la fin de la clôture, l’enregistrement d’audit `term.closed` contient les nombres d’avertissements académiques, d’examens pour exclusion et d’étudiants au tableau d’honneur.
- Codes de sortie : 2 lorsque certains groupes ont des notes non définitives (le nombre de notes non définitives par groupe est affiché). 1 lorsque le semestre n’est pas à l’état publié.
- Quand : une fois la saisie et la validation des notes terminées. Suivez le lot dans Flower et sur l’écran des bilans semestriels. Sans worker Celery, le statut du semestre ne change pas. Une tranche qui échoue sur une erreur de base de données est retentée jusqu’à 3 fois ; si elle échoue encore, le lot reste en échec et le semestre ne change pas (corrigez la cause et relancez ; une nouvelle exécution donne le même résultat).
- Exemples : `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py term_close 2026-FA --reason="Fall 2026 grades closed" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- Objet : recalcule les bilans semestriels (crédits, moyenne du semestre et moyenne cumulée) à partir des notes définitives. À utiliser pour appliquer une règle de notation modifiée (décimales de la moyenne, traitement des reprises) aux semestres passés. La situation académique et le tableau d’honneur conservent les valeurs déterminées à la clôture du semestre. Une modification de note approuvée recalcule automatiquement l’étudiant concerné : cette commande n’est donc pas nécessaire dans ce cas.
- Options : `--term=` (étudiants ayant des notes dans ce semestre, à partir de ce semestre), `--student-number=` (un seul étudiant), `--reason=` (obligatoire), `--actor=`.
- Audit : enregistré (nombre d’étudiants, motif)
- Codes de sortie : 1 sans motif, ou pour un code de semestre ou un numéro d’étudiant inconnu.
- Exemple : `uv run manage.py grades_recalculate --term=2026-SP --reason="GPA changed to three decimal places"`

### `grades_remind_missing`

- Objet : envoie un e-mail aux enseignants des groupes dont les notes n’ont pas encore été soumises (non saisies ou enregistrées en brouillon). Les groupes sont regroupés par enseignant en un seul message chacun.
- Arguments/options : `term` code du semestre, `--dry-run` (affiche les destinataires sans envoyer), `--actor=`.
- Audit : enregistré (groupes, enseignants, messages envoyés)
- Quand : quelques jours avant la clôture de la période de saisie des notes. Ajoutez-la à la planification si nécessaire.
- Exemple : `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## Évaluation des enseignements (phase 7)

### `evaluation_remind`

- Objet : envoie un e-mail aux étudiants qui ont encore des cours non évalués pendant que la période d’évaluation des enseignements est ouverte. Les cours restants sont regroupés par étudiant en un seul message (dans la langue du destinataire).
- Arguments/options : `term` code du semestre, `--dry-run` (nombre d’étudiants concernés uniquement, rien n’est envoyé), `--actor=`.
- Audit : enregistré (étudiants concernés, messages envoyés)
- Codes de sortie : 1 pour un code de semestre inconnu.
- Quand : une ou deux fois pendant la période d’évaluation. Ajoutez-la à la planification si nécessaire.
- Exemple : `uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- Objet : publie aux enseignants les résultats de l’évaluation des enseignements du semestre. Identique à **Évaluation des enseignements > Évaluations par semestre > Publier les résultats** dans le panneau d’administration. Même après la publication, les résultats ne sont visibles que pour les groupes ayant atteint le nombre minimum de réponses et le taux de réponse.
- Arguments/options : `term` code du semestre, `--actor=` (un compte disposant de `Gérer les questionnaires d’évaluation, les évaluations par semestre et leur publication` ; enregistré comme auteur de la publication).
- Audit : enregistré (nombre de réponses, publication déjà faite ou non). Audit métier `evaluation.published`.
- Codes de sortie : 1 pour un code de semestre inconnu ou un semestre sans évaluation des enseignements.
- Quand : une fois la période d’évaluation et le traitement des notes terminés. Un semestre déjà publié n’est pas modifié.
- Exemple : `uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## Attestations (phase 8)

### `certificate_verify`

- Objet : vérifie un code de vérification d’attestation selon les mêmes critères que la page de vérification publique. Affiche le type, le numéro de série, la date de délivrance et le titulaire masqué.
- Arguments/options : `code` code de vérification (la casse n’a pas d’importance).
- Audit : aucun (lecture seule)
- Codes de sortie : 0 si valide, 2 pour un code inconnu, une attestation révoquée ou une durée de validité expirée.
- Exemple : `uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- Objet : régénère le PDF d’une attestation délivrée avec les données et le modèle actuels, en remplaçant le fichier stocké. Identique à **Attestations > Attestations délivrées > Régénérer** dans le panneau d’administration. Le numéro de série et le code de vérification restent les mêmes ; la somme de contrôle change. Le PDF est produit par Gotenberg.
- Arguments/options : `issue` numéro de série, `--reason=` (obligatoire), `--actor=` (un compte disposant de `Délivrer, régénérer et révoquer des attestations`).
- Audit : enregistré (numéro de série, nouvelle somme de contrôle) ; audit métier `certificate.rerendered`.
- Codes de sortie : 1 sans motif, pour un numéro de série inconnu, ou lorsque le PDF ne peut pas être produit.
- Quand : pour régénérer une attestation donnée après la correction d’un modèle, de l’orthographe d’un nom ou de `APP_URL`.
- Exemple : `uv run manage.py certificate_render ENR-2026-000001 --reason="Name spelling corrected"`

## Examens (phase 9)

### `assessment_import_results`

- Objet : saisit depuis un CSV les résultats d’une session d’examen. Mêmes règles que **Sessions d’examen > Importer les résultats (CSV)** dans le panneau d’administration (étudiants inscrits uniquement, réussite décidée à partir des notes, une nouvelle saisie avant la publication remplace le résultat, après la publication les lignes sont signalées comme erreurs).
- Arguments/options : `type` code du type d’examen / `held_date` date de l’examen `YYYY-MM-DD` / `file` un CSV UTF-8 avec ligne d’en-tête, `--actor=` (obligatoire, enregistré comme la personne ayant saisi les résultats), `--dry-run` (validation des lignes uniquement, rien n’est enregistré).
- Format des colonnes : [manuel d’administration, chapitre 24](../admin/24-assessments.md).
- Audit : enregistré (session, nom du fichier, nombre de lignes, nombres de saisies, d’absents et d’erreurs). Chaque résultat reçoit aussi l’entrée d’audit métier `assessment.result_recorded`.
- Codes de sortie : 1 lorsque la session est introuvable, que le fichier ne peut pas être lu ou que `--actor` manque ; 2 en présence de lignes en erreur (les autres lignes sont enregistrées).
- Exemple : `uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- Objet : publie aux étudiants les résultats d’une session. Identique à **Sessions d’examen > Publier les résultats** dans le panneau d’administration. Après la publication, les résultats ne changent que par des demandes de correction.
- Arguments/options : `type` code du type d’examen / `held_date` date de l’examen, `--actor=` (obligatoire, avec l’autorisation d’inscrire des étudiants, de saisir et de publier des résultats).
- Audit : enregistré (session, nombre de résultats) et l’entrée d’audit métier `assessment.results_published`
- Codes de sortie : 1 lorsque la session est introuvable, déjà publiée, que `--actor` manque ou ne dispose pas de l’autorisation.
- Quand : une fois la saisie des résultats terminée.
- Exemple : `uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## Assiduité (phase 10)

### `attendance_generate_sessions`

- Objet : crée les séances de tous les groupes d’un semestre à partir de leurs horaires (jour de la semaine, heure, créneau). Identique à **Générer à partir des horaires** dans le portail enseignant et à **Générer les séances** dans l’onglet **Séances** du panneau d’administration. Les séances existantes et leurs présences sont conservées (peut être relancée sans risque). Les groupes annulés sont ignorés.
- Arguments/options : `term` code du semestre, `--section=` (code du cours-code du groupe, par exemple `CSE2010-01`, un seul), `--dry-run` (nombre de groupes concernés uniquement), `--actor=`.
- Audit : enregistré (semestre, groupes, séances créées)
- Quand : avant le début du semestre, une fois les horaires arrêtés. Relancez-la lorsque les horaires changent.
- Exemple : `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## Diplomation (phase 11)

### `degree_audit_run`

- Objet : enregistre une vérification des conditions d’obtention du diplôme pour chaque étudiant inscrit. Identique à **Vérifications du diplôme > Lancer les vérifications** dans le panneau d’administration. La dernière vérification enregistrée sert de base au traitement des diplomations. Chaque exécution ajoute de nouveaux instantanés.
- Options : `--term=` (code du semestre auquel appartient la vérification), `--student-number=` (un seul étudiant), `--min-year-level=` (uniquement cette année d’études et au-delà), `--actor=`.
- Audit : enregistré (nombre d’étudiants, nombre de vérifications satisfaites). Avec `--actor`, l’audit métier `graduation.audits_run` est également enregistré.
- Codes de sortie : 1 pour un code de semestre inconnu.
- Quand : avant l’examen des diplomations (fin de semestre), et après la modification des ensembles de conditions ou des cours équivalents.
- Exemple : `uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## Intégration LMS (phase 12)

### `lms_sync`

- Objet : pousse les groupes publiés vers la plateforme (création et liaison des cours, enseignants, étudiants inscrits). Fait pour tout un semestre ce que fait **Liens de cours > Synchroniser à nouveau** dans le panneau d’administration. Les groupes déjà liés sont seulement reconfirmés (idempotente). Chaque étape est conservée dans les **Journaux de synchronisation**.
- Arguments/options : `{platform}` code de la plateforme, `--term=` (code du semestre, par défaut tous les semestres non terminés), `--section=` (un code du cours-code du groupe, par exemple `CSE2010-01`), `--dry-run` (enregistre seulement ce qui serait envoyé comme « skipped »), `--actor=`.
- Audit : enregistré (plateforme, groupes, membres, échecs)
- Codes de sortie : 1 pour un code de plateforme ou de semestre inconnu, 2 lorsqu’un groupe a échoué (l’erreur de chaque groupe est affichée).
- Quand : avant le début du semestre, après l’activation d’une nouvelle plateforme.
- Exemple : `uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- Objet : compare les listes de membres des cours de la plateforme avec les listes d’inscription du système d’information étudiant, ajoute les membres manquants et retire ceux en trop. Les groupes pas encore liés sont synchronisés en entier. Les différences sont conservées dans le journal de synchronisation (`reconcile`, `missing` et `extra` dans le `payload`).
- Arguments/options : `{platform?}` (toutes les plateformes actives si omis), `--term=` (par défaut les semestres non terminés), `--dry-run` (enregistre uniquement les différences), `--actor=`.
- Audit : enregistré (groupes par plateforme, nombres d’ajouts, de retraits et d’échecs)
- Codes de sortie : 1 pour un code de plateforme ou de semestre inconnu ou lorsqu’aucune plateforme n’est active, 2 lorsqu’un groupe a échoué.
- Quand : planifiée tous les jours à 02:30 sous la forme de la tâche `lms.reconcile` (Celery beat). À lancer manuellement après une panne de la plateforme.

### `api_issue_token`

- Objet : émet un jeton d’intégration API pour un compte ([ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md)), généralement un compte de service ne disposant que des autorisations nécessaires (LMS : `lms.manage`, BI : `reports.view`). Le jeton est affiché **une seule fois**, sur la première ligne de la sortie standard ; la base de données n’en conserve que l’empreinte. Les requêtes l’envoient dans l’en-tête `Authorization: Token <token>`.
- Arguments/options : `{email}` e-mail du compte, `--days=` (durée de validité de 1 à 365 jours, par défaut `API_TOKEN_TTL_DAYS` = 90), `--reason=` (usage prévu, enregistré dans l’audit), `--actor=`.
- Audit : enregistré (`api.token_issued` : préfixe de la clé et expiration ; jamais le jeton lui-même)
- Codes de sortie : 1 pour un compte inconnu ou inactif ou une durée de validité hors limites.
- Exemple : `uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle callbacks" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- Objet : révoque les jetons API d’un compte (tous, ou un seul avec `--key=`). `--list` se contente de lister les jetons (préfixe de la clé, heures d’émission et d’expiration).
- Arguments/options : `{email}`, `--key=` (préfixe de la clé), `--list`, `--reason=`, `--actor=`.
- Audit : enregistré (`api.token_revoked` : les préfixes de clés révoqués)
- Codes de sortie : 1 pour un compte inconnu ou en l’absence de jeton correspondant à `--key`.
- Quand : à la fin d’une intégration, en cas de fuite possible d’un jeton, ou lorsque la personne responsable change.

## Contrôles d’exploitation et nettoyage (phase 13)

### `system_health_check`

- Objet : contrôle la configuration et les clés (`DJANGO_SECRET_KEY`, clés PII, `DEBUG`), la connexion et les rôles de la base de données (runtime, migrator, reporting), la RLS des tables de données personnelles, les migrations en attente, la synchronisation du catalogue d’autorisations, Redis, les workers Celery, Gotenberg, l’écriture dans le stockage privé et le signal de vie de beat (`core.heartbeat`, de moins de 5 minutes).
- Options : `--json` (sortie destinée à la supervision).
- Audit : aucun (lecture seule)
- Codes de sortie : 2 lorsqu’un contrôle échoue.
- Quand : juste après un déploiement, en cas de suspicion de panne, périodiquement depuis la supervision. Les répartiteurs de charge utilisent `/api/v1/health/`.
- Exemples

  ```bash
  uv run manage.py system_health_check
  uv run manage.py system_health_check --json
  ```

### `audit_seal`

- Objet : relie les nouvelles lignes des tables d’audit (`audit.record_changes`, `audit.activity_log`, `audit.security_events`) à la chaîne de hachage ([intégrité de l’audit](audit-and-maintenance.md)). S’exécute sur la connexion du propriétaire du schéma (`migrator`).
- Options : `--table=` (record_changes, activity_log ou security_events ; répétable), `--actor=`.
- Audit : enregistré (lignes scellées par table)
- Quand : planifiée tous les jours à 03:30.
- Exemples

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- Objet : recalcule les empreintes de contenu et la chaîne des lignes d’audit pour détecter les falsifications, les suppressions et les réordonnancements. Affiche, pour chaque table, les lignes vérifiées, les lignes scellées, les incohérences et le premier identifiant incohérent.
- Options : `--table=`.
- Audit : aucun (lecture seule)
- Codes de sortie : 2 en cas d’incohérence.
- Quand : avant les sauvegardes, lors des revues de sécurité, après une purge.

### `audit_prune`

- Objet : supprime les lignes d’audit **scellées** au-delà de leur durée de conservation. S’exécute sur la connexion du propriétaire du schéma dans une transaction avec `app.audit_maintenance = on`. Les lignes non scellées sont conservées (exécutez d’abord `audit_seal`). Chaque suppression enregistre l’événement de sécurité `audit.pruned` (table, date limite, lignes supprimées, plage d’identifiants, `chain_hash` de la ligne limite).
- Options : `--before=YYYY-MM-DD` (obligatoire ; lignes antérieures à minuit ce jour-là), `--table=`, `--dry-run` (comptage uniquement), `--actor=`.
- Audit : enregistré (date limite, lignes supprimées et plage d’identifiants par table)
- Quand : selon la politique de conservation, après une sauvegarde.
- Exemples

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu
  ```

### `media_prune_orphans`

- Objet : supprime les lignes de médias dont le propriétaire n’existe plus et les répertoires (`<media id>/`) du stockage privé sans ligne correspondante (photos des personnes, pièces de candidature, PDF d’attestations, justificatifs d’examen).
- Options : `--dry-run` (liste uniquement), `--actor=`.
- Audit : enregistré (lignes, répertoires)
- Quand : tous les mois ou après une suppression en masse.

## Clés de chiffrement des données personnelles (phase 0)

### `pii_generate_key`

- Objet : affiche de nouvelles clés (32 octets, `base64:...`) pour `PII_ENCRYPTION_KEY` et `PII_HASH_KEY`. N’enregistre rien.
- Audit : non enregistré
- Attention : changer `PII_HASH_KEY` invalide toutes les empreintes de recherche (`*_hash`). Ne faites tourner que la clé de chiffrement : déplacez l’ancienne clé dans `PII_PREVIOUS_KEYS`, puis exécutez `pii_reencrypt`.
- Exemples

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- Objet : après une rotation de clé, rechiffre avec la clé actuelle les données personnelles chiffrées avec une clé précédente. S’exécute sous la forme d’un groupe de tâches Celery sur des tranches d’enregistrements. Les enregistrements déjà chiffrés avec la clé actuelle ne sont pas modifiés.
- Arguments : le modèle comportant des champs de données personnelles chiffrés (`app_label.Model`, par ex. `person.Person`).
- Options : `--chunk=500` (enregistrements par tâche), `--dry-run` (compte uniquement les enregistrements utilisant une clé précédente), `--force` (sans confirmation), `--actor=`.
- Audit : enregistré (identifiant du lot, nombre de tâches / nombre en aperçu)
- Vérification : suivez les tâches dans Flower. Une fois qu’elles sont terminées et que `--dry-run` indique 0, retirez la clé précédente de `PII_PREVIOUS_KEYS`.
- Exemples

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu
  ```

## Localisation (phase 0)

### `i18n_missing`

- Objet : extrait les chaînes traduisibles du code source comme le fait `makemessages` (sans écrire de fichiers), les compare à tous les catalogues (le `locale/` global et le `locale/` de chaque application) et liste, par langue, les chaînes manquantes (absentes du catalogue, `msgstr` vide, fuzzy, variables différentes) et les entrées obsolètes.
- Arguments/options : `[locale]` (une seule langue, par ex. `ko`, `zh-hans`, `lo`), `--strict` (code de sortie 2 lorsque des chaînes manquent ; utilisé en CI), `--no-extract` (contrôle uniquement les catalogues, sans analyse du code source).
- Audit : non enregistré
- Prérequis : GNU gettext (`xgettext`, `msguniq`).
- Exemples

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- Objet : écrit une feuille destinée aux traducteurs (`.xlsx` ou `.csv`, selon l’extension). Colonnes : `catalog` (emplacement du catalogue), `context`, `source` (msgid anglais), `source_plural`, `translation`, `note` (clé d’origine).
- Arguments/options : `{locale} {path}`, `--missing` (uniquement les chaînes sans traduction).
- Audit : non enregistré
- Exemple : `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- Objet : réécrit dans les catalogues (`.po`) une feuille remplie par les traducteurs et les compile (`.mo`). Seules les chaînes qui existent dans les catalogues (même catalogue, même contexte et même texte anglais) sont importées ; les traductions vides sont ignorées.
- Arguments/options : `{locale} {path}`, `--dry-run` (liste les chaînes qui seraient écrites), `--actor=`.
- Audit : enregistré (langue, nombre de traductions)
- Remarque : les catalogues se trouvent dans le dépôt. Validez (commit) les modifications des `.po` après un import.

### `i18n_makemessages`

- Objet : exécute `makemessages` depuis la racine du dépôt afin que tous les catalogues correspondent au code source (ko, zh_Hans, lo). Les chaînes vont dans le `locale/` de l’application lorsqu’elle en a un, sinon dans le `locale/` global. `.venv`, `tests`, `docs` et les répertoires similaires sont ignorés.
- Options : comme `makemessages` de Django (`-l`, `--no-obsolete`, ...).
- Audit : non enregistré
- Exemple : `uv run manage.py i18n_makemessages`

## Contrôles (phase 0)

### `pdf_sample`

- Objet : rend en PDF un tableau mêlant hangul, CJK, lao, thaï, devanagari, cyrillique et écriture latine afin de vérifier les polices et la connexion au service PDF (Gotenberg).
- Argument : `[path]` (par défaut `pdf-sample.pdf`, relatif au stockage privé des fichiers `PRIVATE_MEDIA_ROOT`).
- Audit : non enregistré
- En cas d’échec : code de sortie 1. Pour les erreurs de connexion, vérifiez `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` et le conteneur Gotenberg.
- Exemple : `uv run manage.py pdf_sample`

### `naming_check`

- Objet : contrôle le schéma de la base de données et le code source au regard des [conventions de nommage](../../../development/naming.md). Elle vérifie les noms des tables et des colonnes dans le catalogue réel de la base de données (schémas `public`, `audit`, `reporting`), les noms des fichiers de migration des applications Ninefruits, les noms des commandes de gestion (`context_action`) ainsi que les msgid et msgctxt des catalogues de traduction (`.po`).
- Règles : snake_case, suffixes interdits (`_old`, `_new`, `_backup`, `_tmp`, dates, nombres), noms contenant un code de langue, colonnes horaires sans fuseau horaire (`timestamp without time zone`), noms des colonnes booléennes (`is_`, `has_`, `can_` ou un verbe), noms des colonnes de date (`_date`), msgid en forme de clés sémantiques (`registration.errors.x`). Les tables définies par Django et par les paquets (`django_*`, allauth, Celery beat, `settings`, `cache`, `jobs`, `media`, etc.) sont exclues.
- Options : `--database=` (connexion de base de données à contrôler, `default` par défaut), `--skip-database` (contrôles des fichiers uniquement, sans base de données).
- Audit : non enregistré
- Code de sortie : 2 lorsque des problèmes sont détectés.
- Exemples

  ```bash
  uv run manage.py naming_check
  ```

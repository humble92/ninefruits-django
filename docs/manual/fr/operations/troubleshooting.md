# Dépannage

- Public : exploitants informatiques
- Voir aussi : [liste de contrôle du déploiement](deployment-checklist.md), [tâches planifiées](scheduled-jobs.md), [référence des commandes](commands.md)

| Symptôme | Points à vérifier |
|---|---|
| Redirection vers la page de sécurité juste après la connexion | La politique de double authentification est « obligatoire » et le délai de grâce est écoulé. Le problème disparaît une fois que l’utilisateur s’est enrôlé. La politique se trouve dans **Paramètres > Sécurité** |
| Erreur 403 dans le panneau d’administration | L’utilisateur n’a aucune attribution de rôle valide comportant l’autorisation `admin_panel.access` (`Ouvrir le panneau d’administration`). Ouvrez l’utilisateur sous **Utilisateurs et accès > Utilisateurs** et vérifiez la liste **Attributions de rôles** (période, périmètre) |
| Une entrée de menu est absente | Le rôle ne dispose pas de l’autorisation correspondant à cet écran (par exemple `roles.view`) |
| Les codes par e-mail n’arrivent pas | Paramètres de messagerie (`MAIL_*`, `DEFAULT_FROM_EMAIL`), entrées `Code par e-mail envoyé` sous **Audit > Événements de sécurité**, limites d’envoi (par utilisateur une fois par minute, cinq fois par heure) |
| La page de connexion répond `429 Too Many Requests` | Une adresse a dépassé `LOGIN_RATE_LIMIT_PER_IP` tentatives par minute (30 par défaut). Si de nombreux utilisateurs sont bloqués en même temps, vérifiez que `TRUSTED_PROXY_COUNT` correspond au nombre réel de proxys (tout le monde apparaissant avec l’adresse de Nginx) ; derrière un NAT de campus, augmentez la valeur ([liste de contrôle du déploiement](deployment-checklist.md#proxys-et-adresse-du-client)) |
| La connexion échoue avec le bon mot de passe | La connexion est verrouillée (`Connexion verrouillée` parmi les **événements de sécurité**) ou le compte est inactif. Levez un verrouillage avec `uv run manage.py security_unlock_user <email> --reason="..."` |
| Un écran affiche 0 ligne pour les données d’autres personnes | Peut être normal (sécurité au niveau des lignes). Vérifiez que l’acteur de la session de base de données est bien défini en consultant la colonne utilisateur dans **Audit > Modifications de données** |
| `400 Bad Request` | Le nom d’hôte demandé ne figure pas dans `DJANGO_ALLOWED_HOSTS` |
| `403 CSRF verification failed` | `DJANGO_CSRF_TRUSTED_ORIGINS` ne contient pas l’adresse `https://`, ou Nginx ne transmet pas `X-Forwarded-Proto` |
| Redirections HTTPS sans fin | Nginx ne transmet pas `X-Forwarded-Proto $scheme` : Django voit donc une requête HTTP (`SECURE_PROXY_SSL_HEADER`) |
| Écrans sans styles ni scripts, erreur `manifest.json` | `npm ci && npm run build` (`static/dist/`), `collectstatic`, la location `/static/` de Nginx. La production utilise `VITE_DEV_MODE=false` |
| Des parties des écrans s’affichent en anglais | `compilemessages --ignore=.venv` n’a pas été exécuté (pas de fichiers `.mo`). Pour les nouvelles chaînes, `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | L’application a tenté une opération DDL en tant que `app_runtime`. Exécutez les migrations uniquement avec `uv run manage.py migrate` ou `setup_install` (qui utilisent tous deux automatiquement `app_migrator`) |
| `Audit records are append-only` | Tentative de mise à jour ou de suppression dans une table d’audit. Ce blocage est voulu |
| La génération des PDF échoue | `uv run manage.py pdf_sample`, état de Gotenberg, `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` |
| Les tâches de file d’attente sont bloquées | Vérifiez la connexion des workers et les tâches en échec dans Flower, `uv run celery -A config inspect active`, la connexion Redis (`REDIS_URL`) |
| Les tâches planifiées ne s’exécutent pas, `/api/v1/health/` répond `degraded` | Beat s’est arrêté (aucun signal de vie du planificateur depuis plus de 5 minutes). Vérifiez le processus beat et son journal. Un seul beat |
| `Received unregistered task` dans le journal du worker | Le worker exécute encore l’ancien code. Redémarrez le worker après le déploiement |
| Une clôture de semestre ne se termine pas | Tâches `grading.close_term_records` en échec dans Flower. Corrigez la cause, puis relancez la clôture du semestre (les calculs par étudiant donnent le même résultat lorsqu’ils sont relancés) |

Traçage par requête : la valeur de l’en-tête de réponse `X-Request-Id` permet de rechercher conjointement dans les journaux (`request_id` dans le JSON), le journal d’activité, les modifications de données et les événements de sécurité. Lorsque Nginx transmet `X-Request-Id $request_id`, le journal d’accès de Nginx s’y ajoute. Les exécutions de commandes utilisent un ID d’exécution commençant par `cmd-`.

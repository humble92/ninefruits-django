# 15. Sign-in methods

Menu: **Settings > Sign-in methods** (`Manage sign-in methods and SSO` permission)

## Sign-in name

The account's email is the default sign-in name. When student number sign-in is turned on, the field on the sign-in screen becomes "Email or student number".

| Sign in with student number | Behaviour |
|---|---|
| Not allowed | Email only |
| Current students only | Student numbers of enrolled and on-leave records can sign in |
| Current students and graduates | Student numbers of ended records (graduated, withdrawn, etc.) can sign in too |

A person with several student records reaches the same account whichever student number they use.

## Account lockout

| Setting | Description |
|---|---|
| Lock after failed attempts | The account is locked when this many wrong passwords are entered in a row. 0 turns locking off |
| Lock duration (minutes) | The lock is lifted automatically after this time |

Attempts by email and by student number count as failures of the same account. A locked account receives the same message as a wrong password, so it does not reveal whether the account exists. Locks are recorded as a security event (**Sign-in locked**).

To lift a lock early, use **Unlock sign-in** on the **Users** detail page (reason required, `Edit users` permission). When the administration panel is unavailable, the IT operator uses `uv run manage.py security_unlock_user`.

## School sign-in (SSO)

Registering the school's OpenID Connect sign-in (for example Microsoft Entra ID, Google Workspace, Keycloak) adds a "Sign in with ..." button to the sign-in screen.

| Field | Description |
|---|---|
| Key | Lowercase identifier, for example `school`. Changing it breaks existing links |
| Button label | The name shown on the sign-in screen |
| Issuer URL | The provider's issuer. `/.well-known/openid-configuration` must be available under this address |
| Client ID, Client secret | Values received when registering the application with the provider. The secret is stored encrypted |
| Scopes | Default `openid email profile` |
| Counts as two-factor authentication | Turn on only when the school sign-in itself requires two-factor authentication. When on, this sign-in is not asked for two-factor authentication here again |
| Redirect URI to register with the provider | Register the address shown on screen (`https://<server>/auth/sso/<key>/callback/`) exactly as it is in the provider's application settings |

### Account linking

| Mode | Behaviour |
|---|---|
| Users link their own accounts | The user signs in with their password and presses **Link** under **Security > School sign-in** in the portal (password confirmation required) |
| Link automatically by verified school email | When the email verified by the provider matches the school email on a student record, the account is linked automatically at the first sign-in |

- Signing in with an unlinked school account shows a notice to sign in with a password and link it. A school account alone never creates a new account.
- Linking and unlinking are recorded in the security log.

### Allowing password sign-in

Turning off **Allow passwords for users with school sign-in** means linked users can only use the school sign-in. Because school accounts often disappear after graduation, we recommend leaving it on and asking students about to graduate to prepare a personal email and password. Graduates keep signing in with the account's sign-in email (personal email) and password.

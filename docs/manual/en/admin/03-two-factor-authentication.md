# 3. Two-factor authentication

## How users enroll

Users enroll on the portal's **Security** page (`/portal/security/`, user menu **Two-factor authentication** in the administration panel). The password is confirmed once more before enrolling or disabling.

### Authenticator app (recommended)

1. Press **Enable two-factor authentication**.
2. Scan the QR code with an authenticator app such as Google Authenticator or Microsoft Authenticator.
3. Enter the 6-digit code shown in the app and press **Confirm**.
4. Store the **recovery codes** shown on screen in a safe place. Each can be used once if the phone is lost.

### Email code

Shown only when the system administrator allows it. It is meant for users who cannot use an authenticator app and is less secure than one.

1. In the **Email code** area, press **Send a code to set up**.
2. Enter the 6-digit code sent to the account email and press **Confirm**.
3. From then on, a code arrives by email at every sign-in. A code can be used once within 10 minutes; after 5 wrong attempts a new code is needed. Codes can be sent once per minute and up to 5 times per hour.

Both methods can be enrolled. When the policy is "required", the last remaining method cannot be disabled.

## Policy settings (system administrator)

Set under **Settings > Security** in the administration panel. Saving applies to every user from their next page load.

| Setting | Description |
|---|---|
| Policy | **Not used** / **Recommended (optional)**: unenrolled users only see a notice / **Required for selected roles**: users holding the selected roles must enroll / **Required for everyone** |
| Roles that must use two-factor authentication | Chosen when the policy is "Required for selected roles" |
| Grace period (days) | How long a user can keep working without enrolling after the requirement first applies to them. During this period a deadline notice appears at the top of the portal and the administration panel. Once it passes, only the security page can be used. 0 means immediately |
| Remember devices for (days) | How long the code is skipped on a device where **Remember this device** was selected. 0 turns this off |
| Allow email codes | When off, email codes do not count as two-factor authentication. Users who only enrolled an email code are asked to enroll an authenticator app according to the policy |

Recommended operation: **Required for selected roles** for staff roles (registrar, academic affairs, system administrator, etc.), recommended for students.

## Reset (lost phone, etc.)

1. Open the user under **Users and access > Users**.
2. Press **Reset two-factor authentication** at the top of the page and enter a reason (requires the `Reset two-factor authentication` permission).
3. The user's authenticator app, recovery codes, email code and remembered devices are all cleared. The grace period starts again.

You cannot reset your own account. The reset is recorded with its reason as a security event and in the activity log.

If the only administrator loses their phone and cannot reach the administration panel, the IT operator resets it with `uv run manage.py security_reset_mfa` (Docker: `docker compose exec app uv run manage.py security_reset_mfa`, [command reference](../operations/commands.md)).

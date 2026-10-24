# 1. Getting started

## Signing in

1. Open `/accounts/login/` in your browser. Opening `/portal/` or `/admin/` while signed out also leads here, and after signing in you return to the page you asked for.
2. Enter your email and password and press **Sign in**.
3. If you have enrolled in two-factor authentication, enter the 6-digit code from your authenticator app or the code you received by email.
4. On a personal computer you can select **Remember this device**. The code is skipped for the configured period (30 days by default). Do not select it on a shared computer.

If you forgot your password, use **Forgot your password?** on the sign-in screen to receive a reset link. Repeated failed sign-ins temporarily block signing in.

The administration panel has no sign-in screen of its own. `/admin/login/` also sends you to the shared sign-in (`/accounts/login/`).

## Portal and administration panel

| Screen | Address | Users |
|---|---|---|
| Portal | `/portal/` | Every user. Home (your access), security settings. Student and instructor features are added in later phases |
| Administration panel | `/admin/` | Staff with the `Open the administration panel` permission |

Both screens share the same sign-in.

- The portal menu at the top shows only the items that match the user's personas (student, instructor, ...) and permissions. With `Open the administration panel`, the **Administration** item leads to the administration panel.
- The user menu at the top right of the administration panel links to **Two-factor authentication** (the portal security settings) and to the **Portal**, and signs you out (**Log out**). The first page (**Dashboard**) shows the account name and email, a portal link and a sign-out button.
- Opening an administration panel address with an account that lacks the permission shows "403 Forbidden".

The menu on the left of the administration panel depends on your permissions. It keeps the original group order (Students and staff, Admissions, Curriculum and sections, Registration, Grades, Course evaluation, Examinations, Certificates, Graduation, Reports, LMS integration, Reference data, Users and access, Audit, Settings); groups without any screen you may open are not shown. If a menu is missing, ask a system administrator for a role assignment. The search field above the menu finds menu entries by name.

## Two-factor notice

When the two-factor policy is "recommended", or during the grace period of a required policy, a notice appears at the top of the portal and the administration panel. **Set up now** opens the portal security page. See [3. Two-factor authentication](03-two-factor-authentication.md).

## Language

Change it with the language selector at the top of the portal (the sign-in screen has the same selector) or with the language list in the administration panel's user menu. When you change it while signed in, the choice is saved on your account and kept for your next sign-in. The system administrator decides which languages are offered under **Settings > Institution**.

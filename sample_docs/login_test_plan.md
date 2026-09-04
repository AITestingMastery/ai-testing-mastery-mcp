# Login Test Plan

## Scope
Covers authentication for the web application: sign-in, sign-out, session
handling, and password reset.

## Test Cases

### Valid login
- Enter a registered email and correct password, click Sign In.
- Expected: user lands on the dashboard within 2 seconds.

### Invalid password
- Enter a registered email with a wrong password.
- Expected: inline error "Incorrect email or password"; no redirect.

### Locked account
- Attempt login 5 times with a wrong password.
- Expected: account locks for 15 minutes; a lockout message is shown.

### Session timeout
- Log in, stay idle for 30 minutes.
- Expected: next action redirects to the login page with a "session expired" notice.

### Password reset
- Click "Forgot password", submit a registered email.
- Expected: reset email sent within 1 minute; link valid for 60 minutes.

## Known Risks
- Login button has intermittently been unresponsive on Chrome (see known bugs).
- Session timeout not always enforced on the reports page.

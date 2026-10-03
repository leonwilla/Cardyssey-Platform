# Cardyssey Security

## Reporting a vulnerability

Please do not disclose vulnerabilities publicly before they are fixed. Report security issues to the private project contact configured for Cardyssey.

Include:
- affected component (Android, web, API or infrastructure)
- reproduction steps
- expected impact
- logs/screenshots without passwords, tokens or private user data

## Security baseline

- TLS/HTTPS only in production.
- JWT secrets and provider credentials only through deployment secrets/environment variables.
- No service-account JSON, Firebase keys, database passwords or signing material in Git.
- Passwords are hashed with Argon2; plaintext passwords must never be logged.
- Refresh tokens are stored server-side as hashes and rotated when consumed.
- Admin/founder routes require server-side authorization; UI hiding is never treated as authorization.
- Uploaded images are decoded/re-encoded and size-limited before serving.
- Authenticated APIs validate resource ownership and friendship/group membership server-side.
- Browser security headers include CSP, frame denial, MIME sniffing protection, referrer policy and permissions policy.
- Dependencies and static analysis should be reviewed continuously.
- Backups of PostgreSQL and persistent catalog/image storage should be encrypted and restore-tested.
- Production logs should avoid access/refresh tokens, Authorization headers, full cookies and private chat bodies unless strictly needed for incident response.

## Before public launch

- [ ] Set real LEGAL_* deployment values and verify Impressum/Datenschutz.
- [ ] Confirm HTTPS/HSTS at the reverse proxy.
- [ ] Rotate JWT/Firebase/database secrets from any development values.
- [ ] Run CodeQL and dependency audit with no unresolved high/critical findings.
- [ ] Verify login/register rate limiting at the reverse proxy/API edge.
- [ ] Verify database is not exposed publicly.
- [ ] Verify Docker services bind only required public ports.
- [ ] Verify admin APIs reject normal users.
- [ ] Verify IDOR tests for collection, wishlist, selling, offers, chats and groups.
- [ ] Verify upload limits and invalid-image handling.
- [ ] Verify account/session revocation and refresh-token rotation.
- [ ] Verify backup restore.
- [ ] Review privacy retention/deletion process.
- [ ] Run an external OWASP ZAP baseline scan against staging.

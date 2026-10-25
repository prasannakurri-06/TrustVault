# TrustVault — Threat Model

## 1. Project Overview

TrustVault is a secure document-sharing web application built with Flask and SQLite. It supports user authentication, document uploads and downloads, document sharing, permission revocation, and audit logging.

## 2. Assets to Protect

- User account credentials
- Uploaded documents and their contents
- Document ownership and sharing permissions
- User sessions and authentication state
- Audit log records
- Application secrets and database contents

## 3. Potential Threats and Mitigations

### T1: Unauthorized Account Access

**Threat:** An attacker may attempt to access another user's account.

**Mitigations:**
- Passwords are stored using password hashing.
- Authentication is required for protected routes.
- Login credentials should never be stored as plaintext passwords.

**Status:** Partially mitigated. Login protection and password handling should be reviewed and tested.

### T2: Unauthorized Document Access

**Threat:** A user may attempt to download a document belonging to another user by changing a document identifier.

**Mitigations:**
- Document ownership is checked on protected download routes.
- Shared-document access is handled through document-sharing permissions.
- Access decisions must be enforced on the server, not only in the interface.

**Status:** Ownership checks and sharing controls are implemented; all routes require authorization testing.

### T3: Malicious File Uploads

**Threat:** An attacker may upload a file intended to exploit the application or its users.

**Mitigations:**
- File extensions are restricted using an allowlist.
- Upload size is limited to 5 MB.
- Stored filenames are randomized instead of using the original filename.
- File upload validation should be enforced on the server.

**Status:** Basic controls are implemented. Extension validation alone cannot guarantee that a file is safe.

### T4: Unauthorized Sharing or Permission Abuse

**Threat:** A user may try to access a shared document without permission or continue accessing it after permission is revoked.

**Mitigations:**
- Document-sharing records associate users with documents and permissions.
- Share and revoke operations should verify the document owner's authority.
- Access permissions should be checked on every relevant request.

**Status:** Sharing and revocation are implemented. The `edit` permission currently does not provide actual document-editing functionality; it must not be represented as a working edit feature.

### T5: Session Misuse

**Threat:** A stolen or improperly managed session may allow unauthorized access.

**Mitigations:**
- Protected routes should require authentication.
- Production deployment should use secure session-cookie settings.
- HTTPS should be enabled in production.
- Session invalidation and logout behavior should be tested.

**Status:** Requires further security review and testing.

### T6: Audit Log Tampering or Missing Events

**Threat:** Security-relevant actions may be missing from the audit trail or records may be altered.

**Mitigations:**
- The application records relevant document and sharing events.
- Audit events should include the acting user, action, timestamp, and relevant document reference when available.
- Audit records should be protected against unauthorized modification.

**Status:** Audit logging is implemented. Strong tamper resistance is not established.

### T7: Cross-Site Scripting (XSS)

**Threat:** Malicious input may be displayed in a way that executes scripts in another user's browser.

**Mitigations:**
- Use template auto-escaping.
- Avoid marking untrusted input as safe HTML.
- Validate and safely display user-controlled filenames and text.

**Status:** Requires testing.

### T8: Cross-Site Request Forgery (CSRF)

**Threat:** A malicious website may attempt to trigger authenticated actions, such as sharing or revoking access.

**Mitigations:**
- Use CSRF protection for state-changing forms and requests.
- Do not rely on authentication alone to prevent forged requests.

**Status:** CSRF protection must be verified before claiming mitigation.

### T9: Secret or Database Exposure

**Threat:** Application secrets, database records, or uploaded files may be exposed through public repositories or incorrect deployment configuration.

**Mitigations:**
- Keep secret keys and sensitive configuration outside source control.
- Exclude local databases, uploaded documents, virtual environments, and secret files from Git.
- Restrict access to database and upload storage.
- Use HTTPS and secure production configuration.

**Status:** Deployment configuration and repository exclusions must be verified.

### T10: Brute-Force Login Attempts

**Threat:** Repeated login attempts may be used to guess account passwords.

**Mitigations:**
- Use strong passwords and secure password hashing.
- Consider login rate limiting and monitoring.
- Avoid revealing whether a username or password alone was incorrect.

**Status:** Rate limiting must be verified or implemented.

## 4. Security Testing Plan

Before release, test the following:

- A logged-out user cannot access protected pages or download files.
- User A cannot download User B's private documents by changing document IDs.
- A user cannot share or revoke documents they do not own.
- Revoked users can no longer access the relevant shared documents.
- Disallowed file types and oversized uploads are rejected.
- User-controlled filenames are safely displayed.
- Logout and session behavior work as expected.
- Audit events are recorded for important actions.
- Secret files, local databases, and uploaded documents are excluded from the public repository.

## 5. Known Limitations

- The `edit` sharing permission does not currently provide document-editing functionality.
- Extension and size checks do not establish that an uploaded file is harmless.
- Audit logging alone does not prevent an administrator or attacker with database access from changing records.
- CSRF protection, rate limiting, production cookie settings, and deployment security must be verified before being described as implemented.

## 6. Responsible Security Practice

Security testing should be performed only on the developer's own application or on systems for which permission has been granted.

## 7. Conclusion

TrustVault implements foundational protections for authentication, document ownership, file uploads, sharing, and audit logging. Further authorization testing and production hardening are necessary before describing the application as production-ready.
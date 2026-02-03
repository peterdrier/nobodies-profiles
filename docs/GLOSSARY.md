# Glossary of Terms

This document explains terms used in the Nobodies Profiles system.

---

## Membership Terms

### Profile
A member's record in the system containing their legal name, country, and membership history. Created automatically when an application is approved.

### Role
A member's level within the organization:
- **Colaborador**: Volunteer/collaborator with basic access
- **Asociado**: Full member with voting rights
- **Board Member**: Administrator with full system access

### Role Assignment
The record linking a member to a role, including start and end dates. Roles expire after 2 years per the statutes.

### Membership Status
The computed state of a member's membership (cannot be set directly):
- **NONE**: Not a member
- **PENDING**: Application submitted, waiting for review
- **APPROVED_PENDING_DOCUMENTS**: Approved but hasn't signed required documents
- **ACTIVE**: Full active member
- **RESTRICTED**: Needs to re-sign updated documents
- **EXPIRED**: Role assignment ended
- **REMOVED**: Removed by board decision

---

## Application Terms

### Application
A request to join the organization, containing personal information and motivation.

### Application Batch
A group of applications reviewed together (optional organizational tool).

### Application Status
- **SUBMITTED**: Just received
- **UNDER_REVIEW**: Board is reviewing
- **APPROVED**: Accepted (creates profile automatically)
- **REJECTED**: Denied

---

## Document Terms

### Legal Document
A document that members must agree to (e.g., Privacy Policy, Code of Conduct).

### Document Version
A specific version of a legal document (e.g., Privacy Policy v1.0, v1.1). Only one version is "current" at a time.

### Spanish Content
The legally binding text. Per Spanish law, the Spanish version is authoritative.

### Translation
Non-binding reference translations in other languages (English, French, etc.).

### Consent Record
A permanent, unchangeable record that a member agreed to a specific document version at a specific time.

### Re-consent
When a document is updated significantly, members must sign the new version. The system tracks this with "Requires re-consent" and a deadline.

---

## Team Terms

### Team
A working group within the organization (e.g., "Events Team", "Communications").

### Team Membership
A record of a member belonging to a team, with their role (Member or Lead).

---

## Tag Terms

### Community Tag
A label for categorizing members (e.g., "Camp Lead", "Freecamper"). Purely decorative - doesn't affect permissions.

### Tag Category
- **EVENT**: Related to events attended
- **SKILL**: Skills the member has
- **RECOGNITION**: Recognition/awards
- **INTEREST**: Personal interests

### Self-Assignable Tag
A tag that members can add/remove themselves (vs. admin-only tags).

---

## GDPR Terms

### GDPR
General Data Protection Regulation - EU law protecting personal data. Gives members rights to access, export, and delete their data.

### Data Export (Right of Access)
A member's right to download all their personal data. The system generates a ZIP file with everything.

### Data Deletion (Right to Erasure)
A member's right to have their data deleted. Requires board review and results in anonymization (not complete deletion, for legal compliance).

### Anonymization
Replacing personal data with placeholder values:
- Email → `deleted_xxx@deleted.nobodies.team`
- Name → `Deleted User #xxx`
- Other personal info → `[REDACTED]`

### Audit Log
A permanent, unchangeable record of all significant actions in the system. Required for GDPR compliance.

---

## Google Drive Terms

### Google Resource
A shared drive, folder, or file in Google Drive that the system manages access to.

### Permission Role
Level of access to a Google resource:
- **Reader**: Can view only
- **Commenter**: Can view and comment
- **Writer**: Can edit
- **Organizer**: Can manage (shared drives only)

### Reconciliation
The daily automatic process that ensures Google Drive permissions match the membership system.

---

## Technical Terms

### Slug
A URL-friendly version of a name using lowercase letters, numbers, and hyphens. Example: "Privacy Policy" → "privacy-policy"

### FSM (Finite State Machine)
A system where something (like an application) moves through defined states in order. Example: SUBMITTED → UNDER_REVIEW → APPROVED.

### Celery Task
A background job that runs automatically. Examples: sending emails, generating exports, syncing Google permissions.

### Migration
A database change. When developers update the system, migrations update the database structure.

---

## Common Abbreviations

| Abbreviation | Meaning |
|--------------|---------|
| GDPR | General Data Protection Regulation |
| PII | Personally Identifiable Information |
| CSV | Comma-Separated Values (spreadsheet format) |
| IP | Internet Protocol (address) |
| OAuth | Open Authorization (Google login system) |
| URL | Uniform Resource Locator (web address) |
| UUID | Universally Unique Identifier (random ID) |

---

*If you encounter a term not listed here, please ask the technical team to add it!*
